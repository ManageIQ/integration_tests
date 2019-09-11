from copy import deepcopy

import pytest

from cfme import test_requirements


@pytest.fixture(scope="function")
def vmdb_config(appliance):
    config = appliance.advanced_settings
    original = deepcopy(config)

    # Check that the default state is None
    assert config['http_proxy']['default']['host'] is None

    yield config
    appliance.update_advanced_settings(original)


def reset_leaf(config):
    config['http_proxy']['default']['host'] = '<<reset>>'


def reset_nonleaf(config):
    config['http_proxy']['default'] = '<<reset>>'


@pytest.mark.parametrize("configurer", (reset_leaf, reset_nonleaf))
@test_requirements.appliance
def test_advanced_config_reset_pzed(appliance, vmdb_config, configurer):
    """Check whether we can use "<<reset>>" string to reset the leaf element
    of the advanced config.

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Configuration
    """

    vmdb_config['http_proxy']['default'] = {'host': 'bar'}
    appliance.update_advanced_settings(vmdb_config)
    config = appliance.advanced_settings
    assert config['http_proxy']['default']['host'] == 'bar'

    configurer(vmdb_config)
    appliance.update_advanced_settings(vmdb_config)
    vmdb_config = appliance.advanced_settings

    # If correctly reset, we should find None as the fixture checked for us
    # that it is the default value.
    assert vmdb_config['http_proxy']['default']['host'] is None
