import argparse
import os
import sys
from collections import deque

import zmq
from py.path import local

import utils.log
from utils import conf


SLAVEID = None


class SlaveManager(object):
    """SlaveManager which coordinates with the master process for parallel testing"""
    def __init__(self, config, slaveid, base_url, zmq_endpoint):
        self.config = config
        self.session = None
        self.collection = None
        self.slaveid = conf.runtime['env']['slaveid'] = slaveid
        self.base_url = conf.runtime['env']['base_url'] = base_url
        conf.clear()
        self.log = utils.log.create_sublogger(self.slaveid)
        # Override the logger in utils.log
        utils.log.logger = utils.log.ArtifactorLoggerAdapter(self.log, {})

        ctx = zmq.Context.instance()
        self.sock = ctx.socket(zmq.REQ)
        self.sock.set_hwm(1)
        self.sock.setsockopt_string(zmq.IDENTITY, u'%s' % self.slaveid)
        self.sock.connect(zmq_endpoint)

        self.messages = {}

    def send_event(self, name, **kwargs):
        kwargs['_event_name'] = name
        self.log.trace("sending %s %r", name, kwargs)
        self.sock.send_json(kwargs)
        recv = self.sock.recv_json()
        if recv == 'die':
            self.log.info('Slave instructed to die by master; shutting down')
            raise SystemExit()
        else:
            self.log.trace('received "%r" from master', recv)
            if recv != 'ack':
                return recv

    def message(self, message):
        """Send a message to the master, which should get printed to the console"""
        self.send_event('message', message=message)  # message!

    def pytest_collection_finish(self, session):
        """pytest collection hook

        - Sends collected tests to the master for comparison

        """
        self.log.debug('collection finished')
        self.session = session
        self.collection = {item.nodeid: item for item in session.items}

    def pytest_runtest_logstart(self, nodeid, location):
        """pytest runtest logstart hook

        - sends logstart notice to the master

        """
        self.send_event("runtest_logstart", nodeid=nodeid, location=location)

    def pytest_runtest_logreport(self, report):
        """pytest runtest logreport hook

        - sends serialized log reports to the master

        """
        self.send_event("runtest_logreport", report=serialize_report(report))

    def pytest_internalerror(self, excrepr):
        """pytest internal error hook

        - logs errors to master console and main logger

        """
        msg = "IERROR> %s" % str(excrepr)
        self.log.error(msg)
        self.message(msg)

    def pytest_sessionfinish(self, exitstatus):
        """pytest session finish hook

        - reports exit status to master; nonblocking to facilitate immediate slave exit

        """
        # Send this non-blocking, quit as soon as possible
        self.send_event('sessionfinish', exit=exitstatus)

    def pytest_runtestloop(self, session):
        """pytest runtest loop

        - iterates over and runs tests in the order received from the master

        """
        self.send_event("collectionfinish", node_ids=self.collection.keys())
        self.message("running tests on appliance at {}".format(self.base_url))
        self.log.info("entering runtest loop")
        for item, nextitem in self._test_generator():
            if self.config.option.collectonly:
                self.message('%s' % (item.nodeid))
                pass
            else:
                self.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)

        self.message('no more tests, shutting down')
        return True

    def _test_generator(self):
        # Pull the first batch of tests, stash in a deque
        tests = self._get_tests()
        while True:
            # pop the first test, try to get the next
            try:
                test_id = tests.popleft()
            except IndexError:
                tests.extend(self._get_tests())
                if not tests:
                    # If tests is empty at this point, no tests were received;
                    # there's nothing to do, and the runtest loop is done
                    break

            try:
                next_test_id = tests[0]
            except IndexError:
                # pytest_runtest_protocol needs an item and a nextitem, so we need to
                # pull new tests before running the last test in the previous test group
                tests.extend(self._get_tests())
                if tests:
                    # We got a new batch of tests, so we can get the next item
                    next_test_id = tests[0]
                else:
                    # no more tests, next test is None
                    next_test_id = None

            test_item = self.collection[test_id]
            if next_test_id:
                next_test_item = self.collection[next_test_id]
            else:
                next_test_item = None
            yield test_item, next_test_item

    def _get_tests(self):
        tests = self.send_event('need_tests')
        return deque(tests)


def serialize_report(rep):
    """
    Get a :py:class:`TestReport <pytest:_pytest.runner.TestReport>` ready to send to the master
    """
    d = rep.__dict__.copy()
    if hasattr(rep.longrepr, 'toterminal'):
        d['longrepr'] = str(rep.longrepr)
    else:
        d['longrepr'] = rep.longrepr
    for name in d:
        if isinstance(d[name], local):
            d[name] = str(d[name])
        elif name == "result":
            d[name] = None
    return d


def _init_config(slave_options, slave_args):
    # Create a pytest Config based on options/args parsed in the master
    # This is a slightly modified form of _pytest.config.Config.fromdictargs
    # yaml is able to pack up the entire CmdOptions call from pytest, so
    # we can just set config.option to what was passed from the master in the slave_config yaml
    from _pytest import config
    pluginmanager = config.get_plugin_manager()
    config = pluginmanager.config
    config.args = slave_args
    config._preparse(config.args, addopts=False)
    config.option = slave_options
    # Unset appliances to prevent the slaves from starting distributes tests :)
    config.option.appliances = []
    for pluginarg in config.option.plugins:
        config.pluginmanager.consider_pluginarg(pluginarg)
    return config


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('slaveid', help='The name of this slave')
    parser.add_argument('base_url', help='The base URL for this slave to use')
    args = parser.parse_args()

    # These must be set before remote_initconfig is called and py.test starts
    # TODO: Not sure this is necessary, since cwd should already be on the path?
    import_path = os.getcwd()
    sys.path.insert(0, import_path)
    os.environ['PYTHONPATH'] = os.path.join(import_path, os.environ.get('PYTHONPATH', ''))

    conf.runtime['env']['slaveid'] = args.slaveid
    conf.runtime['env']['base_url'] = args.base_url

    slave_args = conf.slave_config.pop('args')
    slave_options = conf.slave_config.pop('options')
    config = _init_config(slave_options, slave_args)
    slave_manager = SlaveManager(config, args.slaveid, args.base_url,
        conf.slave_config['zmq_endpoint'])
    config.pluginmanager.register(slave_manager, 'slave_manager')
    config.hook.pytest_cmdline_main(config=config)
