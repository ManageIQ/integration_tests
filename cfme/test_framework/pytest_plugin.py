"""
cfme main plugin

this loads all of the elemental cfme plugins and prepares configuration
"""
import pytest


@pytest.mark.tryfirst
def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme', 'cfme: options related to cfme/miq appliances')


def pytest_configure(config):
    # disable pytest warnings plugin in order to keep our own warning logging
    # we might want to remove this one
    config.pluginmanager.set_blocked('warnings')
    # also disable the pytest logging system since its triggering issues with our own
    config.pluginmanager.set_blocked('logging-plugin')


def pytest_collection_finish(session):
    from cfme.fixtures.pytest_store import store
    store.terminalreporter.write(
        "Uncollection Stats:\n", bold=True)

    for reason, value in store.uncollection_stats.items():
        store.terminalreporter.write(
            " {}: {}\n".format(reason, value), bold=True)
    store.terminalreporter.write(
        " {} tests left after all uncollections\n".format(len(session.items)),
        bold=True)


pytest_plugins = (
    'cfme.markers',
    'cfme.fixtures.pytest_store',
    'cfme.test_framework.sprout.plugin',
    'cfme.test_framework.appliance_police',
    'cfme.test_framework.appliance',
    'cfme.test_framework.appliance_log_collector',
    'cfme.test_framework.browser_isolation',
    'cfme.fixtures.portset',

    'cfme.markers.manual',
    'cfme.markers.polarion',  # before artifactor
    'cfme.markers.env',
    'cfme.fixtures.artifactor_plugin',
    'cfme.fixtures.parallelizer',

    'cfme.fixtures.prov_filter',

    'cfme.fixtures.appliance',
    'cfme.fixtures.ansible_tower',
    'cfme.fixtures.embedded_ansible',
    'cfme.fixtures.single_appliance_sprout',
    'cfme.fixtures.dev_branch',
    'cfme.fixtures.events',
    'cfme.fixtures.appliance_update',
    'cfme.fixtures.blockers',
    'cfme.fixtures.browser',
    'cfme.fixtures.bzs',
    'cfme.fixtures.cfme_data',
    'cfme.fixtures.datafile',
    'cfme.fixtures.depot',
    'cfme.fixtures.disable_forgery_protection',
    'cfme.fixtures.fixtureconf',
    'cfme.fixtures.log',
    'cfme.fixtures.maximized',
    'cfme.fixtures.merkyl',
    'cfme.fixtures.nelson',
    'cfme.fixtures.node_annotate',
    'cfme.fixtures.page_screenshots',
    'cfme.fixtures.perf',
    'cfme.fixtures.provider',
    'cfme.fixtures.physical_switch',
    'cfme.fixtures.qa_contact',
    'cfme.fixtures.randomness',
    'cfme.fixtures.rbac',
    'cfme.fixtures.sauce',
    'cfme.fixtures.screenshots',
    'cfme.fixtures.skip_not_implemented',
    'cfme.fixtures.soft_assert',
    'cfme.fixtures.ssh_client',
    'cfme.fixtures.templateloader',
    'cfme.fixtures.terminalreporter',
    'cfme.fixtures.ui_coverage',
    'cfme.fixtures.update_tests',
    'cfme.fixtures.version_info',
    'cfme.fixtures.video',
    'cfme.fixtures.virtual_machine',
    'cfme.fixtures.widgets',
    'cfme.fixtures.xunit_tools',
    'cfme.fixtures.ansible_fixtures',
    'cfme.fixtures.base',
    'cfme.fixtures.cli',
    'cfme.fixtures.authentication',
    'cfme.fixtures.rdb',
    'cfme.fixtures.service_fixtures',
    'cfme.fixtures.smtp',
    'cfme.fixtures.tag',
    'cfme.fixtures.vm',
    'cfme.fixtures.vm_console',
    'cfme.fixtures.vporizer',
    'cfme.fixtures.model_collections',
    'cfme.fixtures.has_persistent_volume',
    'cfme.fixtures.tccheck',
    'cfme.fixtures.pxe',
    'cfme.fixtures.candu',
    'cfme.fixtures.v2v_fixtures',
    'cfme.fixtures.networks',
    'cfme.fixtures.nuage',
    'cfme.fixtures.automate',
    'cfme.fixtures.multi_region',

    'cfme.metaplugins',
)
