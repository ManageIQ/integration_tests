import signal
from collections import deque
from urlparse import urlparse

import zmq
from py.path import local

SLAVEID = None


class SlaveManager(object):
    """SlaveManager which coordinates with the master process for parallel testing"""
    def __init__(self, config, slaveid, base_url, zmq_endpoint):
        self.config = config
        self.session = None
        self.collection = None
        self.slaveid = conf.runtime['env']['slaveid'] = slaveid
        self.base_url = conf.runtime['env']['base_url'] = base_url
        self.log = utils.log.logger
        conf.clear()
        # Override the logger in utils.log

        ctx = zmq.Context.instance()
        self.sock = ctx.socket(zmq.REQ)
        self.sock.set_hwm(1)
        self.sock.setsockopt_string(zmq.IDENTITY, u'{}'.format(self.slaveid))
        self.sock.connect(zmq_endpoint)

        self.messages = {}

        self.quit_signaled = False

    def send_event(self, name, **kwargs):
        kwargs['_event_name'] = name
        self.log.trace("sending {} {!r}".format(name, kwargs))
        self.sock.send_json(kwargs)
        recv = self.sock.recv_json()
        if recv == 'die':
            self.log.info('Slave instructed to die by master; shutting down')
            raise SystemExit()
        else:
            self.log.trace('received "{!r}" from master'.format(recv))
            if recv != 'ack':
                return recv

    def message(self, message, **kwargs):
        """Send a message to the master, which should get printed to the console"""
        self.send_event('message', message=message, **kwargs)  # message!

    def pytest_collection_finish(self, session):
        """pytest collection hook

        - Sends collected tests to the master for comparison

        """
        self.log.debug('collection finished')
        self.session = session
        self.collection = {item.nodeid: item for item in session.items}
        terminalreporter.disable()
        self.send_event("collectionfinish", node_ids=self.collection.keys())

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

        - logs full traceback
        - reports short traceback to the py.test console

        """
        msg = 'INTERNALERROR> {}'.format(str(excrepr))
        self.log.error(msg)
        # Only send the last line (exc type/message) to keep the pytest log clean
        short_tb = 'INTERNALERROR> {}'.format(msg.strip().splitlines()[-1])
        self.send_event("internalerror", message=short_tb)

    def pytest_runtestloop(self, session):
        """pytest runtest loop

        - iterates over and runs tests in the order received from the master

        """
        self.log.info("entering runtest loop")
        for item, nextitem in self._test_generator():
            if self.config.option.collectonly:
                self.message('{}'.format(item.nodeid))
                pass
            else:
                self.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)
            if self.quit_signaled:
                break
        return True

    def pytest_sessionfinish(self):
        self.shutdown()

    def handle_quit(self):
        self.message('shutting down after the current test due to QUIT signal')
        self.quit_signaled = True

    def shutdown(self):
        self.message('shutting down')
        self.send_event('shutdown')
        self.quit_signaled = True

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
    import pytest  # NOQA
    from _pytest.config import get_config
    config = get_config()
    config.args = slave_args
    config._preparse(config.args, addopts=False)
    config.option = slave_options
    # The master handles the result log, slaves shouldn't also write to it
    config.option['resultlog'] = None
    # Unset appliances to prevent the slaves from starting distributes tests :)
    config.option.appliances = []
    for pluginarg in config.option.plugins:
        config.pluginmanager.consider_pluginarg(pluginarg)
    config.pluginmanager.consider_pluginarg('no:fixtures.parallelizer')
    return config


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('slaveid', help='The name of this slave')
    parser.add_argument('base_url', help='The base URL for this slave to use')
    args = parser.parse_args()

    # overwrite the default logger before anything else is imported,
    # to get our best chance at having everything import the replaced logger
    import utils.log
    slave_logger = utils.log.create_sublogger(args.slaveid)
    utils.log.logger = utils.log.ArtifactorLoggerAdapter(slave_logger, {})

    from fixtures import terminalreporter
    from fixtures.pytest_store import store
    from utils import conf

    conf.runtime['env']['slaveid'] = args.slaveid
    conf.runtime['env']['base_url'] = args.base_url
    store.parallelizer_role = 'slave'

    slave_args = conf.slave_config.pop('args')
    slave_options = conf.slave_config.pop('options')
    ip_address = urlparse(args.base_url).netloc
    appliance_data = conf.slave_config.get("appliance_data", {})
    if ip_address in appliance_data:
        template_name, provider_name = appliance_data[ip_address]
        conf.runtime["cfme_data"]["basic_info"]["appliance_template"] = template_name
        conf.runtime["cfme_data"]["basic_info"]["appliances_provider"] = provider_name
    config = _init_config(slave_options, slave_args)
    slave_manager = SlaveManager(config, args.slaveid, args.base_url,
        conf.slave_config['zmq_endpoint'])
    config.pluginmanager.register(slave_manager, 'slave_manager')
    config.hook.pytest_cmdline_main(config=config)
    signal.signal(signal.SIGQUIT, slave_manager.handle_quit)
