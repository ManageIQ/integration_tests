import pytest
from pages.configuration_subpages.settings_subpages.server_settings_subpages.server_roles import (
    RoleChangesRequired
)
from utils.conf import cfme_data


@pytest.fixture
def server_roles(fixtureconf, cnf_configuration_pg):
    """Set the server roles based on a list of roles attached to the test using this fixture

    Usage:

        If you want to specify certain roles that have to be set,
        you can use this type of decoration:

        @pytest.mark.fixtureconf(server_roles="+automate")
        def test_appliance_roles(server_roles, default_roles_list):
            assert len(server_roles) == len(default_roles_list) + 1

        This takes the current list from cfme_data.yaml and modifies
        it by the server_roles keyword. If prefixed with + or nothing, it adds,
        if prefixed with -, it removes the role. It can be combined either
        in string and in list, so these lines are functionally equivalent:

        "+automate -foo bar" # (add automate and bar, remove foo)
        ["+automate", "-foo", "bar"]

        If you specify the keyword ``clear_roles=True``, then all roles
        are flushed and the list contains only user_interface role.

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

        @pytest.mark.fixtureconf(set_default_roles=True)
        def test_appliance_roles(server_roles):
            do(test)


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
        - rhn_mirror
        - smartproxy
        - smartstate
        - user_interface
        - web_services
    """

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

    if 'clear_roles' in fixtureconf:
        sst.set_server_roles(sst.ui_only_role_list())
    elif 'set_default_roles' in fixtureconf:
        sst.set_server_roles(sst.default_server_roles_list())
    elif 'server_roles' in fixtureconf:
        sst.edit_current_role_list(fixtureconf['server_roles'])
    elif 'server_roles_cfmedata' in fixtureconf:
        roles_list = cfme_data
        # Drills down into cfme_data YAML by selector, expecting a list
        # of roles at the end. A KeyError here probably means the YAMe
        # selector is wrong
        for selector in fixtureconf['server_roles_cfmedata']:
            roles_list = roles_list[selector]
        sst.set_server_roles(roles_list)
    else:
        raise RoleChangesRequired('No server role changes defined.')
