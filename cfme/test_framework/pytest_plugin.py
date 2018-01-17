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


def pytest_collection_finish(session):
    from fixtures.pytest_store import store
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
    'fixtures.pytest_store',
    'cfme.test_framework.sprout.plugin',
    'cfme.test_framework.appliance_police',
    'cfme.test_framework.appliance',
    'cfme.test_framework.appliance_log_collector',
    'cfme.test_framework.browser_isolation',
    'fixtures.portset',

    'cfme.markers.manual',
    'cfme.markers.polarion',  # before artifactor
    'cfme.markers.env',
    'fixtures.artifactor_plugin',
    'fixtures.parallelizer',

    'fixtures.prov_filter',

    'fixtures.appliance',
    'fixtures.single_appliance_sprout',
    'fixtures.dev_branch',
    'fixtures.events',
    'fixtures.appliance_update',
    'fixtures.blockers',
    'fixtures.browser',
    'fixtures.cfme_data',
    'fixtures.disable_forgery_protection',
    'fixtures.datafile',
    'fixtures.fixtureconf',
    'fixtures.log',
    'fixtures.maximized',
    'fixtures.merkyl',
    'fixtures.nelson',
    'fixtures.node_annotate',
    'fixtures.page_screenshots',
    'fixtures.perf',
    'fixtures.provider',
    'fixtures.qa_contact',
    'fixtures.randomness',
    'fixtures.rbac',
    'fixtures.sauce',
    'fixtures.screenshots',
    'fixtures.skip_not_implemented',
    'fixtures.soft_assert',
    'fixtures.ssh_client',
    'fixtures.templateloader',
    'fixtures.terminalreporter',
    'fixtures.ui_coverage',
    'cfme.fixtures.version_info',
    'cfme.fixtures.video',
    'cfme.fixtures.virtual_machine',
    'cfme.fixtures.widgets',
    'cfme.fixtures.xunit_tools',
    'cfme.fixtures.ansible_fixtures',
    'cfme.fixtures.base',
    'cfme.fixtures.cli',
    'cfme.fixtures.configure_auth_mode',
    'cfme.fixtures.rdb',
    'cfme.fixtures.service_fixtures',
    'cfme.fixtures.smtp',
    'cfme.fixtures.tag',
    'cfme.fixtures.vm',
    'cfme.fixtures.vm_name',
    'cfme.fixtures.vm_console',
    'cfme.fixtures.vporizer',
    'cfme.fixtures.model_collections',
    'cfme.fixtures.has_persistent_volume',
    'cfme.fixtures.tccheck',
    'cfme.fixtures.pxe',

    'cfme.metaplugins',
)
