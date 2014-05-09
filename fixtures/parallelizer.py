import sys
import py, pytest

def pytest_addoption(parser):
    group = parser.getgroup("xdist", "distributed and subprocess testing")
    group._addoption('-f', '--looponfail',
           action="store_true", dest="looponfail", default=False,
           help="run tests in subprocess, wait for modified files "
                "and re-run failing test set until all pass.")
    group._addoption('-n', dest="numprocesses", metavar="numprocesses",
           action="store", type="int",
           help="shortcut for '--dist=load --tx=NUM*popen'")
    group.addoption('--boxed',
           action="store_true", dest="boxed", default=False,
           help="box each test run in a separate process (unix)")
    group._addoption('--dist', metavar="distmode",
           action="store", choices=['load', 'each', 'no'],
           type="choice", dest="dist", default="no",
           help=("set mode for distributing tests to exec environments.\n\n"
                 "each: send each test to each available environment.\n\n"
                 "load: send each test to available environment.\n\n"
                 "(default) no: run tests inprocess, don't distribute."))
    group._addoption('--tx', dest="tx", action="append", default=[],
           metavar="xspec",
           help=("add a test execution environment. some examples: "
                 "--tx popen//python=python2.5 --tx socket=192.168.1.102:8888 "
                 "--tx ssh=user@codespeak.net//chdir=testcache"))
    group._addoption('-d',
           action="store_true", dest="distload", default=False,
           help="load-balance tests.  shortcut for '--dist=load'")
    group.addoption('--rsyncdir', action="append", default=[], metavar="dir1",
           help="add directory for rsyncing to remote tx nodes.")

    parser.addini('rsyncdirs', 'list of (relative) paths to be rsynced for'
         ' remote distributed testing.', type="pathlist")
    parser.addini('rsyncignore', 'list of (relative) paths to be ignored '
         'for rsyncing.', type="pathlist")
    parser.addini("looponfailroots", type="pathlist",
        help="directories to check for changes", default=[py.path.local()])

# -------------------------------------------------------------------------
# distributed testing hooks
# -------------------------------------------------------------------------
def pytest_addhooks(pluginmanager):
    from xdist import newhooks
    pluginmanager.addhooks(newhooks)

# -------------------------------------------------------------------------
# distributed testing initialization
# -------------------------------------------------------------------------

def pytest_cmdline_main(config):
    check_options(config)
    if config.getvalue("looponfail"):
        from xdist.looponfail import looponfail_main
        looponfail_main(config)
        return 2 # looponfail only can get stop with ctrl-C anyway

def pytest_configure(config, __multicall__):
    __multicall__.execute()
    if config.getvalue("dist") != "no":
        from xdist.dsession import DSession
        session = DSession(config)
        config.pluginmanager.register(session, "dsession")

def check_options(config):
    if config.option.numprocesses:
        config.option.dist = "load"
        config.option.tx = ['popen'] * int(config.option.numprocesses)
    if config.option.distload:
        config.option.dist = "load"
    val = config.getvalue
    if not val("collectonly"):
        usepdb = config.option.usepdb  # a core option
        if val("looponfail"):
            if usepdb:
                raise pytest.UsageError("--pdb incompatible with --looponfail.")
        elif val("dist") != "no":
            if usepdb:
                raise pytest.UsageError("--pdb incompatible with distributing tests.")


def pytest_runtest_protocol(item):
    if item.config.getvalue("boxed"):
        reports = forked_run_report(item)
        for rep in reports:
            item.ihook.pytest_runtest_logreport(report=rep)
        return True

def forked_run_report(item):
    # for now, we run setup/teardown in the subprocess
    # XXX optionally allow sharing of setup/teardown
    from _pytest.runner import runtestprotocol
    EXITSTATUS_TESTEXIT = 4
    import marshal
    from xdist.remote import serialize_report
    from xdist.slavemanage import unserialize_report
    def runforked():
        try:
            reports = runtestprotocol(item, log=False)
        except KeyboardInterrupt:
            py.std.os._exit(EXITSTATUS_TESTEXIT)
        return marshal.dumps([serialize_report(x) for x in reports])

    ff = py.process.ForkedFunc(runforked)
    result = ff.waitfinish()
    if result.retval is not None:
        report_dumps = marshal.loads(result.retval)
        return [unserialize_report("testreport", x) for x in report_dumps]
    else:
        if result.exitstatus == EXITSTATUS_TESTEXIT:
            py.test.exit("forked test item %s raised Exit" %(item,))
        return [report_process_crash(item, result)]

def report_process_crash(item, result):
    path, lineno = item._getfslineno()
    info = "%s:%s: running the test CRASHED with signal %d" %(
            path, lineno, result.signal)
    from _pytest import runner
    call = runner.CallInfo(lambda: 0/0, "???")
    call.excinfo = info
    rep = runner.pytest_runtest_makereport(item, call)
    return rep

import sys
import difflib

import pytest
import py
from xdist.slavemanage import NodeManager


queue = py.builtin._tryimport('queue', 'Queue')


class EachScheduling:

    def __init__(self, numnodes, log=None):
        self.numnodes = numnodes
        self.node2collection = {}
        self.node2pending = {}
        if log is None:
            self.log = py.log.Producer("eachsched")
        else:
            self.log = log.loadsched
        self.collection_is_completed = False

    def hasnodes(self):
        return bool(self.node2pending)

    def addnode(self, node):
        self.node2collection[node] = None

    def tests_finished(self):
        if not self.collection_is_completed:
            return False
        return True

    def addnode_collection(self, node, collection):
        assert not self.collection_is_completed
        assert self.node2collection[node] is None
        self.node2collection[node] = list(collection)
        self.node2pending[node] = []
        if len(self.node2pending) >= self.numnodes:
            self.collection_is_completed = True

    def remove_item(self, node, item):
        self.node2pending[node].remove(item)

    def remove_node(self, node):
        # KeyError if we didn't get an addnode() yet
        pending = self.node2pending.pop(node)
        if not pending:
            return
        crashitem = pending.pop(0)
        # XXX what about the rest of pending?
        return crashitem

    def init_distribute(self):
        assert self.collection_is_completed
        for node, pending in self.node2pending.items():
            node.send_runtest_all()
            pending[:] = self.node2collection[node]

class LoadScheduling:
    LOAD_THRESHOLD_NEWITEMS = 5
    ITEM_CHUNKSIZE = 10

    def __init__(self, numnodes, log=None):
        self.numnodes = numnodes
        self.node2pending = {}
        self.node2collection = {}
        self.pending = []
        if log is None:
            self.log = py.log.Producer("loadsched")
        else:
            self.log = log.loadsched
        self.collection_is_completed = False

    def hasnodes(self):
        return bool(self.node2pending)

    def addnode(self, node):
        self.node2pending[node] = []

    def tests_finished(self):
        if not self.collection_is_completed or self.pending:
            return False
        #for items in self.node2pending.values():
        #    if items:
        #        return False
        return True

    def addnode_collection(self, node, collection):
        assert not self.collection_is_completed
        assert node in self.node2pending
        self.node2collection[node] = list(collection)
        if len(self.node2collection) >= self.numnodes:
            self.collection_is_completed = True

    def remove_item(self, node, item):
        if item not in self.item2nodes:
            raise AssertionError(item, self.item2nodes)
        nodes = self.item2nodes[item]
        if node in nodes: # the node might have gone down already
            nodes.remove(node)
        #if not nodes:
        #    del self.item2nodes[item]
        pending = self.node2pending[node]
        pending.remove(item)
        # pre-load items-to-test if the node may become ready
        if self.pending and len(pending) < self.LOAD_THRESHOLD_NEWITEMS:
            item = self.pending.pop(0)
            pending.append(item)
            self.item2nodes.setdefault(item, []).append(node)
            node.send_runtest(item)
        self.log("items waiting for node: %d" %(len(self.pending)))
        #self.log("item2pending still executing: %s" %(self.item2nodes,))
        #self.log("node2pending: %s" %(self.node2pending,))

    def remove_node(self, node):
        pending = self.node2pending.pop(node)
        # KeyError if we didn't get an addnode() yet
        for item in pending:
            l = self.item2nodes[item]
            l.remove(node)
            if not l:
                del self.item2nodes[item]
        if not pending:
            return
        crashitem = pending.pop(0)
        self.pending.extend(pending)
        return crashitem

    def init_distribute(self):
        assert self.collection_is_completed
        assert not hasattr(self, 'item2nodes')
        self.item2nodes = {}
        # XXX allow nodes to have different collections
        first_node, col = list(self.node2collection.items())[0]
        for node, collection in self.node2collection.items():
            report_collection_diff(
                col,
                collection,
                first_node.gateway.id,
                node.gateway.id,
            )

        self.pending = col
        if not col:
            return
        available = list(self.node2pending.items())
        num_available = self.numnodes
        max_one_round = num_available * self.ITEM_CHUNKSIZE - 1
        for i, item in enumerate(self.pending):
            nodeindex = i % num_available
            node, pending = available[nodeindex]
            node.send_runtest(item)
            self.item2nodes.setdefault(item, []).append(node)
            pending.append(item)
            if i >= max_one_round:
                break
        del self.pending[:i + 1]

def report_collection_diff(from_collection, to_collection, from_id, to_id):
    """Report the collected test difference between two nodes.

    :returns: True if collections are equal.

    :raises: AssertionError with a detailed error message describing the
             difference between the collections.

    """
    if from_collection == to_collection:
        return True

    diff = difflib.unified_diff(
        from_collection,
        to_collection,
        fromfile=from_id,
        tofile=to_id,
    )
    error_message = py.builtin._totext(
        'Different tests were collected between {from_id} and {to_id}. '
        'The difference is:\n'
        '{diff}'
    ).format(from_id=from_id, to_id=to_id, diff='\n'.join(diff))
    msg = "\n".join([x.rstrip() for x in error_message.split("\n")])
    raise AssertionError(msg)


class Interrupted(KeyboardInterrupt):
    """ signals an immediate interruption. """

class DSession:
    def __init__(self, config):
        self.config = config
        self.log = py.log.Producer("dsession")
        if not config.option.debug:
            py.log.setconsumer(self.log._keywords, None)
        self.shuttingdown = False
        self.countfailures = 0
        self.maxfail = config.getvalue("maxfail")
        self.queue = queue.Queue()
        self._failed_collection_errors = {}
        try:
            self.terminal = config.pluginmanager.getplugin("terminalreporter")
        except KeyError:
            self.terminal = None
        else:
            self.trdist = TerminalDistReporter(config)
            config.pluginmanager.register(self.trdist, "terminaldistreporter")

    def report_line(self, line):
        if self.terminal and self.config.option.verbose >= 0:
            self.terminal.write_line(line)

    @pytest.mark.trylast
    def pytest_sessionstart(self, session):
        self.nodemanager = NodeManager(self.config)
        self.nodemanager.setup_nodes(putevent=self.queue.put)

    def pytest_sessionfinish(self, session):
        """ teardown any resources after a test run. """
        nm = getattr(self, 'nodemanager', None) # if not fully initialized
        if nm is not None:
            nm.teardown_nodes()

    def pytest_collection(self):
        # prohibit collection of test items in master process
        return True

    def pytest_runtestloop(self):
        numnodes = len(self.nodemanager.specs)
        dist = self.config.getvalue("dist")
        if dist == "load":
            self.sched = LoadScheduling(numnodes, log=self.log)
        elif dist == "each":
            self.sched = EachScheduling(numnodes, log=self.log)
        else:
            assert 0, dist
        self.shouldstop = False
        self.session_finished = False
        while not self.session_finished:
            self.loop_once()
            if self.shouldstop:
                raise Interrupted(str(self.shouldstop))
        return True

    def loop_once(self):
        """ process one callback from one of the slaves. """
        while 1:
            try:
                eventcall = self.queue.get(timeout=2.0)
                break
            except queue.Empty:
                continue
        callname, kwargs = eventcall
        assert callname, kwargs
        method = "slave_" + callname
        call = getattr(self, method)
        self.log("calling method: %s(**%s)" % (method, kwargs))
        call(**kwargs)
        if self.sched.tests_finished():
            self.triggershutdown()

    #
    # callbacks for processing events from slaves
    #

    def slave_slaveready(self, node, slaveinfo):
        node.slaveinfo = slaveinfo
        node.slaveinfo['id'] = node.gateway.id
        node.slaveinfo['spec'] = node.gateway.spec
        self.config.hook.pytest_testnodeready(node=node)
        self.sched.addnode(node)
        if self.shuttingdown:
            node.shutdown()

    def slave_slavefinished(self, node):
        self.config.hook.pytest_testnodedown(node=node, error=None)
        if node.slaveoutput['exitstatus'] == 2: # keyboard-interrupt
            self.shouldstop = "%s received keyboard-interrupt" % (node,)
            self.slave_errordown(node, "keyboard-interrupt")
            return
        crashitem = self.sched.remove_node(node)
        #assert not crashitem, (crashitem, node)
        if self.shuttingdown and not self.sched.hasnodes():
            self.session_finished = True

    def slave_errordown(self, node, error):
        self.config.hook.pytest_testnodedown(node=node, error=error)
        try:
            crashitem = self.sched.remove_node(node)
        except KeyError:
            pass
        else:
            if crashitem:
                self.handle_crashitem(crashitem, node)
                #self.report_line("item crashed on node: %s" % crashitem)
        if not self.sched.hasnodes():
            self.session_finished = True

    def slave_collectionfinish(self, node, ids):
        self.sched.addnode_collection(node, ids)
        if self.terminal:
            self.trdist.setstatus(node.gateway.spec, "[%d]" %(len(ids)))

        if self.sched.collection_is_completed:
            if self.terminal:
                self.trdist.ensure_show_status()
                self.terminal.write_line("")
                self.terminal.write_line("scheduling tests via %s" %(
                    self.sched.__class__.__name__))

            self.sched.init_distribute()

    def slave_logstart(self, node, nodeid, location):
        self.config.hook.pytest_runtest_logstart(
            nodeid=nodeid, location=location)

    def slave_testreport(self, node, rep):
        if not (rep.passed and rep.when != "call"):
            if rep.when in ("setup", "call"):
                self.sched.remove_item(node, rep.nodeid)
        #self.report_line("testreport %s: %s" %(rep.id, rep.status))
        rep.node = node
        self.config.hook.pytest_runtest_logreport(report=rep)
        self._handlefailures(rep)

    def slave_collectreport(self, node, rep):
        if rep.failed:
            self._failed_slave_collectreport(node, rep)

    def _failed_slave_collectreport(self, node, rep):
        # Check we haven't already seen this report (from
        # another slave).
        if rep.longrepr not in self._failed_collection_errors:
            self._failed_collection_errors[rep.longrepr] = True
            self.config.hook.pytest_collectreport(report=rep)
            self._handlefailures(rep)

    def _handlefailures(self, rep):
        if rep.failed:
            self.countfailures += 1
            if self.maxfail and self.countfailures >= self.maxfail:
                self.shouldstop = "stopping after %d failures" % (
                    self.countfailures)

    def triggershutdown(self):
        self.log("triggering shutdown")
        self.shuttingdown = True
        for node in self.sched.node2pending:
            node.shutdown()

    def handle_crashitem(self, nodeid, slave):
        # XXX get more reporting info by recording pytest_runtest_logstart?
        runner = self.config.pluginmanager.getplugin("runner")
        fspath = nodeid.split("::")[0]
        msg = "Slave %r crashed while running %r" %(slave.gateway.id, nodeid)
        rep = runner.TestReport(nodeid, (fspath, None, fspath), (),
            "failed", msg, "???")
        rep.node = slave
        self.config.hook.pytest_runtest_logreport(report=rep)

class TerminalDistReporter:
    def __init__(self, config):
        self.config = config
        self.tr = config.pluginmanager.getplugin("terminalreporter")
        self._status = {}
        self._lastlen = 0

    def write_line(self, msg):
        self.tr.write_line(msg)

    def ensure_show_status(self):
        if not self.tr.hasmarkup:
            self.write_line(self.getstatus())

    def setstatus(self, spec, status, show=True):
        self._status[spec.id] = status
        if show and self.tr.hasmarkup:
            self.rewrite(self.getstatus())

    def getstatus(self):
        parts = ["%s %s" %(spec.id, self._status[spec.id])
                   for spec in self._specs]
        return " / ".join(parts)

    def rewrite(self, line, newline=False):
        pline = line + " " * max(self._lastlen-len(line), 0)
        if newline:
            self._lastlen = 0
            pline += "\n"
        else:
            self._lastlen = len(line)
        self.tr.rewrite(pline, bold=True)

    def pytest_xdist_setupnodes(self, specs):
        self._specs = specs
        for spec in specs:
            self.setstatus(spec, "I", show=False)
        self.setstatus(spec, "I", show=True)
        self.ensure_show_status()

    def pytest_xdist_newgateway(self, gateway):
        if self.config.option.verbose > 0:
            rinfo = gateway._rinfo()
            version = "%s.%s.%s" % rinfo.version_info[:3]
            self.rewrite("[%s] %s Python %s cwd: %s" % (
                gateway.id, rinfo.platform, version, rinfo.cwd),
                newline=True)
        self.setstatus(gateway.spec, "C")

    def pytest_testnodeready(self, node):
        if self.config.option.verbose > 0:
            d = node.slaveinfo
            infoline = "[%s] Python %s" %(
                d['id'],
                d['version'].replace('\n', ' -- '),)
            self.rewrite(infoline, newline=True)
        self.setstatus(node.gateway.spec, "ok")

    def pytest_testnodedown(self, node, error):
        if not error:
            return
        self.write_line("[%s] node down: %s" %(node.gateway.id, error))

    #def pytest_xdist_rsyncstart(self, source, gateways):
    #    targets = ",".join([gw.id for gw in gateways])
    #    msg = "[%s] rsyncing: %s" %(targets, source)
    #    self.write_line(msg)
    #def pytest_xdist_rsyncfinish(self, source, gateways):
    #    targets = ", ".join(["[%s]" % gw.id for gw in gateways])
    #    self.write_line("rsyncfinish: %s -> %s" %(source, targets))

"""
    This module is executed in remote subprocesses and helps to
    control a remote testing session and relay back information.
    It assumes that 'py' is importable and does not have dependencies
    on the rest of the xdist code.  This means that the xdist-plugin
    needs not to be installed in remote environments.
"""

import sys, os

class SlaveInteractor:
    def __init__(self, config, channel):
        self.config = config
        self.slaveid = config.slaveinput.get('slaveid', "?")
        self.log = py.log.Producer("slave-%s" % self.slaveid)
        if not config.option.debug:
            py.log.setconsumer(self.log._keywords, None)
        self.channel = channel
        config.pluginmanager.register(self)

    def sendevent(self, name, **kwargs):
        self.log("sending", name, kwargs)
        self.channel.send((name, kwargs))

    def pytest_internalerror(self, excrepr):
        for line in str(excrepr).split("\n"):
            self.log("IERROR> " + line)

    def pytest_sessionstart(self, session):
        self.session = session
        slaveinfo = getinfodict()
        self.sendevent("slaveready", slaveinfo=slaveinfo)

    def pytest_sessionfinish(self, __multicall__, exitstatus):
        self.config.slaveoutput['exitstatus'] = exitstatus
        res = __multicall__.execute()
        self.sendevent("slavefinished", slaveoutput=self.config.slaveoutput)
        return res

    def pytest_collection(self, session):
        self.sendevent("collectionstart")

    def pytest_runtestloop(self, session):
        self.log("entering main loop")
        torun = []
        while 1:
            name, kwargs = self.channel.receive()
            self.log("received command %s(**%s)" % (name, kwargs))
            if name == "runtests":
                ids = kwargs['ids']
                for nodeid in ids:
                    torun.append(self._id2item[nodeid])
            elif name == "runtests_all":
                torun.extend(session.items)
            self.log("items to run: %s" %(len(torun)))
            while len(torun) >= 2:
                item = torun.pop(0)
                nextitem = torun[0]
                self.config.hook.pytest_runtest_protocol(item=item,
                    nextitem=nextitem)
            if name == "shutdown":
                while torun:
                    self.config.hook.pytest_runtest_protocol(
                        item=torun.pop(0), nextitem=None)
                break
        return True

    def pytest_collection_finish(self, session):
        self._id2item = {}
        ids = []
        for item in session.items:
            self._id2item[item.nodeid] = item
            ids.append(item.nodeid)
        self.sendevent("collectionfinish",
            topdir=str(session.fspath),
            ids=ids)

    #def pytest_runtest_logstart(self, nodeid, location, fspath):
    #    self.sendevent("logstart", nodeid=nodeid, location=location)

    def pytest_runtest_logreport(self, report):
        data = serialize_report(report)
        self.sendevent("testreport", data=data)

    def pytest_collectreport(self, report):
        data = serialize_report(report)
        self.sendevent("collectreport", data=data)

def serialize_report(rep):
    import py
    d = rep.__dict__.copy()
    if hasattr(rep.longrepr, 'toterminal'):
        d['longrepr'] = str(rep.longrepr)
    else:
        d['longrepr'] = rep.longrepr
    for name in d:
        if isinstance(d[name], py.path.local):
            d[name] = str(d[name])
        elif name == "result":
            d[name] = None # for now
    return d

def getinfodict():
    import platform
    return dict(
        version = sys.version,
        version_info = tuple(sys.version_info),
        sysplatform = sys.platform,
        platform = platform.platform(),
        executable = sys.executable,
        cwd = os.getcwd(),
    )

def remote_initconfig(option_dict, args):
    from _pytest.config import Config
    option_dict['plugins'].append("no:terminal")
    config = Config.fromdictargs(option_dict, args)
    config.option.looponfail = False
    config.option.usepdb = False
    config.option.dist = "no"
    config.option.distload = False
    config.option.numprocesses = None
    config.args = args
    return config


if __name__ == '__channelexec__':
    # python3.2 is not concurrent import safe, so let's play it safe
    # https://bitbucket.org/hpk42/pytest/issue/347/pytest-xdist-and-python-32
    if sys.version_info[:2] == (3,2):
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    slaveinput,args,option_dict = channel.receive()
    importpath = os.getcwd()
    sys.path.insert(0, importpath) # XXX only for remote situations
    os.environ['PYTHONPATH'] = (importpath + os.pathsep +
        os.environ.get('PYTHONPATH', ''))
    #os.environ['PYTHONPATH'] = importpath
    import py
    config = remote_initconfig(option_dict, args)
    config.slaveinput = slaveinput
    config.slaveoutput = {}
    interactor = SlaveInteractor(config, channel)
    config.hook.pytest_cmdline_main(config=config)

import py, pytest
import sys, os
import execnet
import xdist.remote

from _pytest import runner # XXX load dynamically

class NodeManager(object):
    EXIT_TIMEOUT = 10
    def __init__(self, config, specs=None, defaultchdir="pyexecnetcache"):
        self.config = config
        self._nodesready = py.std.threading.Event()
        self.trace = self.config.trace.get("nodemanager")
        self.group = execnet.Group()
        if specs is None:
            specs = self._getxspecs()
        self.specs = []
        for spec in specs:
            if not isinstance(spec, execnet.XSpec):
                spec = execnet.XSpec(spec)
            if not spec.chdir and not spec.popen:
                spec.chdir = defaultchdir
            self.group.allocate_id(spec)
            self.specs.append(spec)
        self.roots = self._getrsyncdirs()

    def rsync_roots(self):
        """ make sure that all remote gateways
            have the same set of roots in their
            current directory.
        """
        options = {
            'ignores': self.config.getini("rsyncignore"),
            'verbose': self.config.option.verbose,
        }
        if self.roots:
            # send each rsync root
            for root in self.roots:
                self.rsync(root, **options)

    def makegateways(self):
        assert not list(self.group)
        self.config.hook.pytest_xdist_setupnodes(config=self.config,
            specs=self.specs)
        for spec in self.specs:
            gw = self.group.makegateway(spec)
            self.config.hook.pytest_xdist_newgateway(gateway=gw)

    def setup_nodes(self, putevent):
        self.makegateways()
        self.rsync_roots()
        self.trace("setting up nodes")
        for gateway in self.group:
            node = SlaveController(self, gateway, self.config, putevent)
            gateway.node = node  # to keep node alive
            node.setup()
            self.trace("started node %r" % node)

    def teardown_nodes(self):
        self.group.terminate(self.EXIT_TIMEOUT)

    def _getxspecs(self):
        xspeclist = []
        for xspec in self.config.getvalue("tx"):
            i = xspec.find("*")
            try:
                num = int(xspec[:i])
            except ValueError:
                xspeclist.append(xspec)
            else:
                xspeclist.extend([xspec[i+1:]] * num)
        if not xspeclist:
            raise pytest.UsageError(
                "MISSING test execution (tx) nodes: please specify --tx")
        return [execnet.XSpec(x) for x in xspeclist]

    def _getrsyncdirs(self):
        for spec in self.specs:
            if not spec.popen or spec.chdir:
                break
        else:
            return []
        import pytest, _pytest
        pytestpath = pytest.__file__.rstrip("co")
        pytestdir = py.path.local(_pytest.__file__).dirpath()
        config = self.config
        candidates = [py._pydir,pytestpath,pytestdir]
        candidates += config.option.rsyncdir
        rsyncroots = config.getini("rsyncdirs")
        if rsyncroots:
            candidates.extend(rsyncroots)
        roots = []
        for root in candidates:
            root = py.path.local(root).realpath()
            if not root.check():
                raise pytest.UsageError("rsyncdir doesn't exist: %r" %(root,))
            if root not in roots:
                roots.append(root)
        return roots

    def rsync(self, source, notify=None, verbose=False, ignores=None):
        """ perform rsync to all remote hosts.
        """
        rsync = HostRSync(source, verbose=verbose, ignores=ignores)
        seen = py.builtin.set()
        gateways = []
        for gateway in self.group:
            spec = gateway.spec
            if spec.popen and not spec.chdir:
                # XXX this assumes that sources are python-packages
                # and that adding the basedir does not hurt
                gateway.remote_exec("""
                    import sys ; sys.path.insert(0, %r)
                """ % os.path.dirname(str(source))).waitclose()
                continue
            if spec not in seen:
                def finished():
                    if notify:
                        notify("rsyncrootready", spec, source)
                rsync.add_target_host(gateway, finished=finished)
                seen.add(spec)
                gateways.append(gateway)
        if seen:
            self.config.hook.pytest_xdist_rsyncstart(
                source=source,
                gateways=gateways,
            )
            rsync.send()
            self.config.hook.pytest_xdist_rsyncfinish(
                source=source,
                gateways=gateways,
            )

class HostRSync(execnet.RSync):
    """ RSyncer that filters out common files
    """
    def __init__(self, sourcedir, *args, **kwargs):
        self._synced = {}
        ignores= None
        if 'ignores' in kwargs:
            ignores = kwargs.pop('ignores')
        self._ignores = ignores or []
        super(HostRSync, self).__init__(sourcedir=sourcedir, **kwargs)

    def filter(self, path):
        path = py.path.local(path)
        if not path.ext in ('.pyc', '.pyo'):
            if not path.basename.endswith('~'):
                if path.check(dotfile=0):
                    for x in self._ignores:
                        if path == x:
                            break
                    else:
                        return True

    def add_target_host(self, gateway, finished=None):
        remotepath = os.path.basename(self._sourcedir)
        super(HostRSync, self).add_target(gateway, remotepath,
                                          finishedcallback=finished,
                                          delete=True,)

    def _report_send_file(self, gateway, modified_rel_path):
        if self._verbose:
            path = os.path.basename(self._sourcedir) + "/" + modified_rel_path
            remotepath = gateway.spec.chdir
            py.builtin.print_('%s:%s <= %s' %
                              (gateway.spec, remotepath, path))


def make_reltoroot(roots, args):
    # XXX introduce/use public API for splitting py.test args
    splitcode = "::"
    l = []
    for arg in args:
        parts = arg.split(splitcode)
        fspath = py.path.local(parts[0])
        for root in roots:
            x = fspath.relto(root)
            if x or fspath == root:
                parts[0] = root.basename + "/" + x
                break
        else:
            raise ValueError("arg %s not relative to an rsync root" % (arg,))
        l.append(splitcode.join(parts))
    return l

class SlaveController(object):
    ENDMARK = -1

    def __init__(self, nodemanager, gateway, config, putevent):
        self.nodemanager = nodemanager
        self.putevent = putevent
        self.gateway = gateway
        self.config = config
        self.slaveinput = {'slaveid': gateway.id}
        self._down = False
        self.log = py.log.Producer("slavectl-%s" % gateway.id)
        if not self.config.option.debug:
            py.log.setconsumer(self.log._keywords, None)

    def __repr__(self):
        return "<%s %s>" %(self.__class__.__name__, self.gateway.id,)

    def setup(self):
        self.log("setting up slave session")
        spec = self.gateway.spec
        args = self.config.args
        if not spec.popen or spec.chdir:
            args = make_reltoroot(self.nodemanager.roots, args)
        option_dict = vars(self.config.option)
        if spec.popen:
            name = "popen-%s" % self.gateway.id
            basetemp = self.config._tmpdirhandler.getbasetemp()
            option_dict['basetemp'] = str(basetemp.join(name))
        self.config.hook.pytest_configure_node(node=self)
        self.channel = self.gateway.remote_exec(xdist.remote)
        self.channel.send((self.slaveinput, args, option_dict))
        if self.putevent:
            self.channel.setcallback(self.process_from_remote,
                endmarker=self.ENDMARK)

    def ensure_teardown(self):
        if hasattr(self, 'channel'):
            if not self.channel.isclosed():
                self.log("closing", self.channel)
                self.channel.close()
            #del self.channel
        if hasattr(self, 'gateway'):
            self.log("exiting", self.gateway)
            self.gateway.exit()
            #del self.gateway

    def send_runtest(self, nodeid):
        self.sendcommand("runtests", ids=[nodeid])

    def send_runtest_all(self):
        self.sendcommand("runtests_all",)

    def shutdown(self):
        if not self._down:
            try:
                self.sendcommand("shutdown")
            except IOError:
                pass

    def sendcommand(self, name, **kwargs):
        """ send a named parametrized command to the other side. """
        self.log("sending command %s(**%s)" % (name, kwargs))
        self.channel.send((name, kwargs))

    def notify_inproc(self, eventname, **kwargs):
        self.log("queuing %s(**%s)" % (eventname, kwargs))
        self.putevent((eventname, kwargs))

    def process_from_remote(self, eventcall):
        """ this gets called for each object we receive from
            the other side and if the channel closes.

            Note that channel callbacks run in the receiver
            thread of execnet gateways - we need to
            avoid raising exceptions or doing heavy work.
        """
        try:
            if eventcall == self.ENDMARK:
                err = self.channel._getremoteerror()
                if not self._down:
                    if not err or isinstance(err, EOFError):
                        err = "Not properly terminated" # lost connection?
                    self.notify_inproc("errordown", node=self, error=err)
                    self._down = True
                return
            eventname, kwargs = eventcall
            if eventname in ("collectionstart"):
                self.log("ignoring %s(%s)" %(eventname, kwargs))
            elif eventname == "slaveready":
                self.notify_inproc(eventname, node=self, **kwargs)
            elif eventname == "slavefinished":
                self._down = True
                self.slaveoutput = kwargs['slaveoutput']
                self.notify_inproc("slavefinished", node=self)
            #elif eventname == "logstart":
            #    self.notify_inproc(eventname, node=self, **kwargs)
            elif eventname in ("testreport", "collectreport", "teardownreport"):
                rep = unserialize_report(eventname, kwargs['data'])
                self.notify_inproc(eventname, node=self, rep=rep)
            elif eventname == "collectionfinish":
                self.notify_inproc(eventname, node=self, ids=kwargs['ids'])
            else:
                raise ValueError("unknown event: %s" %(eventname,))
        except KeyboardInterrupt:
            # should not land in receiver-thread
            raise
        except:
            excinfo = py.code.ExceptionInfo()
            py.builtin.print_("!" * 20, excinfo)
            self.config.pluginmanager.notify_exception(excinfo)

def unserialize_report(name, reportdict):
    d = reportdict
    if name == "testreport":
        return runner.TestReport(**d)
    elif name == "collectreport":
        return runner.CollectReport(**d)
