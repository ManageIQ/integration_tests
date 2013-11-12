import logging

import pytest
from unittestzero import Assert

logger = logging.getLogger(__name__)

default_roles = (
    'database_operations',
    'event',
    'ems_inventory',
    'ems_operations',
    'reporting',
    'scheduler',
    'smartstate',
    'user_interface',
    'web_services',
)

@pytest.fixture
def server_roles(fixtureconf, cfme_data, cnf_configuration_pg):
    """Set the server roles based on a list of roles attached to the test using this fixture

    Usage examples:

        Pass the desired roles in to the "server_roles_set" decorator:

        _roles = ('database_operations', 'event', 'user_interface', 'web_services')

        @pytest.mark.fixtureconf(server_roles=_roles)
        def test_appliance_roles(server_roles):
            assert len(server_roles) == 4

        Roles can be pulled from the cfme_data fixture using yaml selectors,
        which will do a 'set' with the list of roles found at the target path:

        @pytest.mark.fixtureconf(server_roles_cfmedata=('level1', 'sublevel2'))
        def test_appliance_roles(server_roles):
            assert len(server_roles) == 3

        Which corresponds to this yaml layout:

        level1:
            sublevel2:
                - database_operations
                - user_interface
                - web_services

        To ensure the appliance has the default roles:

        from fixtures.server_roles import default_roles

        @pytest.mark.fixtureconf(server_roles=default_roles)
        def test_appliance_roles(server_roles):
            assert len(server_roles) == len(default_roles)

    List of server role names currently exposed in the CFME interface:

        - automate
        - ems_metrics_coordinator
        - ems_metrics_collector
        - ems_metrics_processor
        - database_operations
        - database_synchronization
        - event
        - ems_inventory
        - ems_operations
        - notifier
        - reporting
        - scheduler
        - smartproxy
        - smartstate
        - user_interface
        - web_services

    """

    if 'server_roles' in fixtureconf:
        roles_list = list(fixtureconf['server_roles'])
    elif 'server_roles_cfmedata' in fixtureconf:
        roles_list = cfme_data.data
        # Drills down into cfme_data YAML by selector, expecting a list
        # of roles at the end. A KeyError here probably means the YAMe
        # selector is wrong
        for selector in fixtureconf['server_roles_cfmedata']:
            roles_list = roles_list[selector]
    else:
        raise Exception('server_roles config not found on test callable')

    # Deselecting the user interface role is really un-fun, and is
    # counterproductive in the middle of user interface testing.
    if 'user_interface' not in roles_list:
        raise Exception('Refusing to remove the user_interface role')

    # Nav to the settings tab
    settings_pg = cnf_configuration_pg.click_on_settings()
    # Workaround to rudely bypass a popup that sometimes appears for
    # unknown reasons.
    # See also: https://github.com/RedHatQE/cfme_tests/issues/168
    from pages.configuration_subpages.settings_subpages.server_settings import ServerSettings
    server_settings_pg = ServerSettings(settings_pg.testsetup)
    # sst is a configuration_subpages.settings_subpages.server_settings_subpages.
    #   server_settings_tab.ServerSettingsTab
    sst = server_settings_pg.click_on_server_tab()

    # Set the roles!
    if sorted(sst.selected_server_role_names) != sorted(roles_list):
        sst.set_server_roles(roles_list)
        sst.save()
        sst._wait_for_results_refresh()
    else:
        logger.info('Server roles already match configured fixture roles, not changing server roles')

    # If this assert fails, check roles names for typos or other minor differences
    Assert.equal(sorted(sst.selected_server_role_names), sorted(roles_list))

    return sst.selected_server_role_names

