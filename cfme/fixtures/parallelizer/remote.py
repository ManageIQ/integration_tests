import json
import signal

import zmq
from py.path import local

import cfme.utils
from cfme.fixtures.log import _format_nodeid
from cfme.fixtures.log import _test_status
from cfme.utils import log
from cfme.utils.appliance import find_appliance

SLAVEID = None


class SlaveManager(object):
    """SlaveManager which coordinates with the master process for parallel testing"""
    def __init__(self, config, slaveid, zmq_endpoint):
        self.config = config
        self.session = None
        self.collection = None
        self.slaveid = conf['env']['slaveid'] = slaveid
        self.log = cfme.utils.log.logger
        # Override the logger in utils.log

        ctx = zmq.Context.instance()
        self.sock = ctx.socket(zmq.REQ)
        self.sock.set_hwm(1)
        self.sock.setsockopt_string(zmq.IDENTITY, '{}'.format(self.slaveid))
        self.sock.connect(zmq_endpoint)

        self.messages = {}

        self.quit_signaled = False

    def send_event(self, name, **kwargs):
        kwargs['_event_name'] = name
        self.log.debug("sending {} {!r}".format(name, kwargs))
        self.sock.send_json(kwargs)
        recv = self.sock.recv_json()
        if recv == 'die':
            self.log.info('Slave instructed to die by master; shutting down')
            raise SystemExit()
        else:
            self.log.debug('received "{!r}" from master'.format(recv))
            if recv != 'ack':
                return recv

    def message(self, message, **kwargs):
        """Send a message to the master, which should get printed to the console"""
        self.send_event('message', message=message, markup=kwargs)  # message!

    def pytest_collection_finish(self, session):
        """pytest collection hook

        - Sends collected tests to the master for comparison

        """
        self.log.debug('collection finished')
        self.session = session
        self.collection = {item.nodeid: item for item in session.items}
        terminalreporter.disable()
        self.send_event("collectionfinish", node_ids=list(self.collection.keys()))

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
        if report.when == 'teardown':
            path, lineno, domaininfo = report.location
            test_status = _test_status(_format_nodeid(report.nodeid, False))
            if test_status == "failed":
                appliance = find_appliance(self)
                try:
                    self.log.info(
                        "Managed providers: {}".format(
                            ", ".join([
                                prov.key for prov in
                                appliance.managed_known_providers]))
                    )
                except KeyError as ex:
                    if 'ext_management_systems' in ex.msg:
                        self.log.warning("Unable to query ext_management_systems table; DB issue")
                    else:
                        raise
            self.log.info(log.format_marker('{} result: {}'.format(_format_nodeid(report.nodeid),
                                                                   test_status)),
                          extra={'source_file': path, 'source_lineno': lineno})
        if report.outcome == "skipped":
            self.log.info(log.format_marker(report.longreprtext))

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
        node_iter = self._iter_nodes()
        try:
            run_node = next(node_iter)
        except StopIteration:
            return []

        for next_node in node_iter:
            yield run_node, next_node
            run_node = next_node
        yield run_node, None

    def _iter_nodes(self):
        while True:
            node_ids = self.send_event('need_tests')
            if not node_ids:
                break
            for nodeid in node_ids:
                # TODO: take non-unique node ids into account
                yield self.collection[nodeid]


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
    config.option.__dict__.update(slave_options)
    # The master handles the result log, slaves shouldn't also write to it
    config.option.resultlog = None
    # Unset appliances to prevent the slaves from starting distributes tests :)
    config.option.appliances = []
    config.pluginmanager.set_blocked('cfme.fixtures.parallelizer')
    for pluginarg in config.option.plugins:
        config.pluginmanager.consider_pluginarg(pluginarg)
    return config


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', help='The worker id of this process')
    parser.add_argument('--appliance', help='The json data about the used appliance')
    parser.add_argument('--ts', help='The timestap to use for collections')

    parser.add_argument('--config', help='The timestap to use for collections')
    args = parser.parse_args()

    # TODO: clean the logic up here

    from cfme.utils.appliance import IPAppliance, stack

    # overwrite the default logger before anything else is imported,
    # to get our best chance at having everything import the replaced logger
    import cfme.utils.log
    cfme.utils.log.setup_for_worker(args.worker)
    slave_log = cfme.utils.log.logger

    try:
        appliance = IPAppliance.from_json(args.appliance)
    except ValueError:
        slave_log.error("Error parsing appliance json")
        raise
    else:
        stack.push(appliance)

    try:
        config = json.loads(args.config)
    except ValueError:
        slave_log.error("Error parsing pytest config from json")

    from cfme.fixtures import terminalreporter
    from cfme.fixtures.pytest_store import store
    from cfme.utils import conf

    conf['env']['slaveid'] = args.worker
    conf['env']['ts'] = args.ts
    store.parallelizer_role = 'slave'

    slave_args = config.pop('args')
    slave_options = config.pop('options')
    ip_address = appliance.hostname
    appliance_data = config["appliance_data"]
    if ip_address in appliance_data:
        template_name, provider_name = appliance_data[ip_address]
        conf["cfme_data"]["basic_info"]["appliance_template"] = template_name
        conf["cfme_data"]["basic_info"]["appliances_provider"] = provider_name
    pytest_config = _init_config(slave_options, slave_args)
    slave_manager = SlaveManager(pytest_config, args.worker, config['zmq_endpoint'])
    pytest_config.pluginmanager.register(slave_manager, 'slave_manager')
    pytest_config.hook.pytest_cmdline_main(config=pytest_config)
    signal.signal(signal.SIGQUIT, slave_manager.handle_quit)
