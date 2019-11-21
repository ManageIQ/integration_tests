from urllib.parse import urlparse

import attr
import pytest

from cfme.fixtures import terminalreporter
from cfme.fixtures.pytest_store import store
from cfme.utils import conf
from cfme.utils.appliance import DummyAppliance
from cfme.utils.appliance import load_appliances_from_config
from cfme.utils.appliance import stack
from cfme.utils.path import log_path

PLUGIN_KEY = "appliance-holder"


def pytest_addoption(parser):
    group = parser.getgroup("cfme")
    # common appliance options
    group.addoption('--app-version', default=None, dest='appliance-version')

    # dummy appliance type
    group.addoption('--use-dummy-apps', action='store_true', default=False)
    group.addoption('--num-dummy-apps', default=1, type=int)

    # dev/local appliance type
    group.addoption('--use-local-apps', action='store_true', default=False)

    # regular appliance type
    group.addoption('--no-regular-apps', action='store_false', default=True)
    group.addoption('--num-regular-apps', action=1, type=int)

    # pod appliance type
    group.addoption('--use-pod-apps', action='store_true', default=False)
    group.addoption('--num-pod-apps', action=1, type=int)
    # todo: add below options
    # --sprout-template-type=openshift_pod
    # --sprout-ignore-preconfigured

    # multi-region appliance type
    group.addoption('--use-mr-apps', action='store_true', default=False,
                    dest='use-multi-region-apps')
    group.addoption('--num-mr-apps', action=1, type=int, dest='num-multi-region-apps')

    # some providers aren't suitable for multi-region tests due to issues with floating IP and etc
    group.addoption('--mr-apps-provider-type', default='rhevm',
                    dest='multi-region-apps-provider-type')
    group.addoption('--num-mr-apps-remote-nodes', action=1, type=int,
                    dest='num-multi-region-apps-remote-nodes')

    # upgraded appliance type
    group.addoption('--use-upgraded-apps', action='store_true', default=False)
    group.addoption('--upgraded-apps-versions-from', default=[], action='append')


def appliances_from_cli(cli_appliances, appliance_version):
    appliance_config = dict(appliances=[])
    for appliance_data in cli_appliances:
        parsed_url = urlparse(appliance_data['hostname'])
        if not parsed_url.hostname:
            raise ValueError(
                "Invalid appliance url: {}".format(appliance_data)
            )

        appliance = appliance_data.copy()
        appliance.update(dict(
            hostname=parsed_url.hostname,
            ui_protocol=parsed_url.scheme if parsed_url.scheme else "https",
            ui_port=parsed_url.port if parsed_url.port else 443,
            version=appliance_version
        ))

        appliance_config['appliances'].append(appliance)

    return load_appliances_from_config(appliance_config)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):

    if config.getoption('--help'):
        return
    reporter = terminalreporter.reporter()
    if config.getoption('--dummy-appliance'):
        appliances = [
            DummyAppliance.from_config(config) for _ in range(config.getoption('--num-dummies'))
        ]
        reporter.write_line('Retrieved Dummy Appliance', red=True)
    elif stack.top:
        appliances = [stack.top]
    elif config.option.appliances:
        appliances = appliances_from_cli(config.option.appliances, config.option.appliance_version)
        reporter.write_line('Retrieved these appliances from the --appliance parameters', red=True)
    elif config.getoption('--use-sprout'):
        from cfme.test_framework.sprout.plugin import mangle_in_sprout_appliances

        mangle_in_sprout_appliances(config)
        # TODO : handle direct sprout pass on?
        appliances = appliances_from_cli(config.option.appliances, None)
        reporter.write_line('Retrieved these appliances from the --sprout-* parameters', red=True)
    else:
        appliances = load_appliances_from_config(conf.env)
        reporter.write_line('Retrieved these appliances from the conf.env', red=True)

    if not stack.top:
        for appliance in appliances:
            reporter.write_line('* {!r}'.format(appliance), cyan=True)
    appliance = appliances[0]
    if not appliance.is_dev:
        appliance.set_session_timeout(86400)
    stack.push(appliance)
    plugin = ApplianceHolderPlugin(appliance, appliances)
    config.pluginmanager.register(plugin, PLUGIN_KEY)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure():
    stack.pop()


@attr.s(cmp=False)
class ApplianceHolderPlugin(object):
    held_appliance = attr.ib()
    appliances = attr.ib(default=attr.Factory(list))

    def pytest_sessionstart(self):
        # TODO: izapolsk move somewhere
        if isinstance(self.held_appliance, DummyAppliance) or self.held_appliance.is_dev:
            return
        if store.parallelizer_role != 'slave':
            with log_path.join('appliance_version').open('w') as appliance_version:
                appliance_version.write(self.held_appliance.version.vstring)
