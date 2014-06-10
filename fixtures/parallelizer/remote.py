"""execnet remote runner"""
import os
import sys

from utils import conf
import utils.log


class SlaveInteractor:
    def __init__(self, config, channel):
        self.config = config
        self.slaveid = conf.runtime['env']['slaveid'] = config.slaveinput['slaveid']
        self.base_url = conf.runtime['env']['base_url'] = config.slaveinput['base_url']
        # Override the base_url for this process and set the slave_id
        self.log = utils.log.create_sublogger('slave-%s' % self.slaveid)
        self.log.info('slave started with slaveinput: %r' % self.config.slaveinput)
        utils.log.logger = self.log
        self.channel = channel
        config.pluginmanager.register(self)

    def sendevent(self, name, **kwargs):
        self.log.debug("sending %s %r", name, kwargs)
        self.channel.send((name, kwargs))

    def pytest_internalerror(self, excrepr):
        for line in str(excrepr).split("\n"):
            self.log.error("IERROR> %s", line)

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
        self.log.info("entering main loop")
        torun = []
        while 1:
            name, kwargs = self.channel.receive()
            self.log.debug("received command %s %r", name, kwargs)
            if name == "runtests":
                torun.extend(kwargs['indices'])
                self.log.debug('torun: %r', torun)
            elif name == "runtests_all":
                torun.extend(range(len(session.items)))
            self.log.info("items to run: %d tests", len(torun))
            while torun:
                self.run_tests(torun)
            if name == "shutdown":
                break
        return True

    def run_tests(self, torun):
        items = self.session.items
        self.item_index = torun.pop(0)
        item = items[self.item_index]
        if torun:
            nextitem = items[torun[0]]
        else:
            nextitem = None

        if self.config.option.collectonly:
            module, testname = item.nodeid.rsplit('::', 1)
            message = '%s: %s' % (module, str(item))
            self.sendevent('message', message=message)
        else:
            self.config.hook.pytest_runtest_protocol(
                item=item, nextitem=nextitem)

        if not nextitem:
            self.sendevent("needs_tests")

    def pytest_collection_finish(self, session):
        self.log.debug('collection finished')
        self.sendevent("collectionfinish",
            topdir=str(session.fspath),
            ids=[item.nodeid for item in session.items])

    def pytest_runtest_logstart(self, nodeid, location):
        self.sendevent("logstart", nodeid=nodeid, location=location)

    def pytest_runtest_logreport(self, report):
        data = serialize_report(report)
        data["item_index"] = self.item_index
        assert self.session.items[self.item_index].nodeid == report.nodeid
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
            d[name] = None
    return d


def getinfodict():
    import platform
    return {
        'version': sys.version,
        'version_info': tuple(sys.version_info),
        'sysplatform': sys.platform,
        'platform': platform.platform(),
        'executable': sys.executable,
        'cwd': os.getcwd(),
    }


def remote_initconfig(option_dict, args):
    from _pytest.config import Config
    option_dict['plugins'].append("no:terminal")
    config = Config.fromdictargs(option_dict, args)
    config.option.appliances = []
    config.args = args
    return config


if __name__ == '__channelexec__':
    # python3.2 is not concurrent import safe, so let's play it safe
    # https://bitbucket.org/hpk42/pytest/issue/347/pytest-xdist-and-python-32
    channel = globals()['channel']
    slaveinput, args, option_dict = channel.receive()
    # These must be set before remote_initconfig is called and py.test starts
    conf.runtime['env']['slaveid'] = slaveinput['slaveid']
    conf.runtime['env']['base_url'] = slaveinput['base_url']
    importpath = os.getcwd()
    sys.path.insert(0, importpath)
    os.environ['PYTHONPATH'] = (importpath + os.pathsep +
        os.environ.get('PYTHONPATH', ''))
    #os.environ['PYTHONPATH'] = importpath
    config = remote_initconfig(option_dict, args)
    config.slaveinput = slaveinput
    config.slaveoutput = {}
    interactor = SlaveInteractor(config, channel)
    config.hook.pytest_cmdline_main(config=config)
