# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [test_requirements.configuration]


@pytest.fixture(scope="module")
def configured_external_appliance(temp_appliance_preconfig, app_creds_modscope,
                                  temp_appliance_unconfig):
    hostname = temp_appliance_preconfig.hostname
    temp_appliance_unconfig.appliance_console_cli.configure_appliance_external_join(hostname,
        app_creds_modscope['username'], app_creds_modscope['password'], 'vmdb_production',
        hostname, app_creds_modscope['sshlogin'], app_creds_modscope['sshpass'])
    temp_appliance_unconfig.evmserverd.start()
    temp_appliance_unconfig.evmserverd.wait_for_running()
    temp_appliance_unconfig.wait_for_web_ui()
    return temp_appliance_unconfig


def test_remote_server_advanced_config(temp_appliance_preconfig, request,
                                       configured_external_appliance):
    """
    Test that starting in 5.10 it is possible to modify advanced settings for remote servers
    BZ1536524

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Configuration
    """
    appliance = temp_appliance_preconfig
    remote_server = appliance.server.secondary_servers[0]
    #  Advanced tab exists for remote servers
    navigate_to(remote_server, 'Advanced')

    # change one setting
    initial_conf = remote_server.advanced_settings['server']['startup_timeout']
    request.addfinalizer(lambda: appliance.update_advanced_settings(
        {'server': {'startup_timeout': initial_conf}}))
    remote_server.update_advanced_settings({'server': {'startup_timeout': initial_conf * 2}})
    new_conf = remote_server.advanced_settings['server']['startup_timeout']
    assert new_conf == initial_conf * 2
