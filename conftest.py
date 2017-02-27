"""
Top-level conftest.py does a couple of things:

1) Add cfme_pages repo to the sys.path automatically
2) Load a number of plugins and fixtures automatically
"""

import pytest


@pytest.mark.tryfirst
def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme', 'cfme: options related to cfme/miq appliances')


pytest_plugins = (
    'markers',
    'fixtures.pytest_store',
    'cfme.test_framework.sprout.plugin',
    'cfme.test_framework.appliance_police',

    'fixtures.portset',


    'markers.polarion',  # before artifactor
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
    'fixtures.screenshots',
    'fixtures.soft_assert',
    'fixtures.ssh_client',
    'fixtures.templateloader',
    'fixtures.terminalreporter',
    'fixtures.ui_coverage',
    'fixtures.version_file',
    'fixtures.video',
    'fixtures.virtual_machine',
    'fixtures.widgets',

    'markers',

    'cfme.fixtures.base',
    'cfme.fixtures.cli',
    'cfme.fixtures.pytest_selenium',
    'cfme.fixtures.configure_auth_mode',
    'cfme.fixtures.rdb',
    'cfme.fixtures.rest_api',
    'cfme.fixtures.service_fixtures',
    'cfme.fixtures.smtp',
    'cfme.fixtures.tag',
    'cfme.fixtures.vm_name',
    'cfme.fixtures.rand_fake_metrics',
    'cfme.fixtures.vporizer',
    'cfme.fixtures.setup_chargeback_generation_interval',

    'cfme.metaplugins',
)

# work around pytest bug
# https://github.com/pytest-dev/pytest/issues/2353
pytest.register_assert_rewrite(*pytest_plugins)
