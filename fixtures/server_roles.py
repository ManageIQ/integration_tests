import logging

import pytest
import re

logger = logging.getLogger(__name__)


@pytest.fixture
def server_roles_categories(cfme_data):
    """ Provides the ``server_roles`` section from cfme_data
    """
    return cfme_data.get("server_roles", {})


@pytest.fixture
def default_roles_list(server_roles_categories):
    """ Provides the list of default roles enabled from cfme_data
    """
    return server_roles_categories.get("default", [])


@pytest.fixture
def server_roles(fixtureconf, cfme_data, default_roles_list, cnf_configuration_pg):
    """Set the server roles based on a list of roles attached to the test using this fixture

    Usage:

        If you want to specify certain roles that have to be set,
        you can use this type of decoration:

        @pytest.mark.fixtureconf(server_roles="+automate")
        def test_appliance_roles(server_roles, default_roles_list):
            assert len(server_roles) == len(default_roles_list) + 1

        This takes the default list from cfme_data.yaml and modifies
        it by the server_roles keyword. If prefixed with + or nothing, it adds,
        if prefixed with -, it removes the role. It can be combined either
        in string and in list, so these lines are functionally equivalent:

        "+automate -foo bar" # (add automate and bar, remove foo)
        ["+automate", "-foo", "bar"]

        If you specify the keyword ``clear_default_roles=True``, then all roles
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

        @pytest.mark.fixtureconf(server_roles=None)
        def test_appliance_roles(server_roles):
            do(test)

        This works because if a ``None`` parameter for server_roles is passed,
        default roles are used and no modification will be done.

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
        roles_list = default_roles_list[:]
        if "clear_default_roles" in fixtureconf:
            if fixtureconf['clear_default_roles']:
                roles_list = ["user_interface"]  # This must be
        # Modify it according to the server_roles
        server_roles_list = fixtureconf['server_roles']
        # Break the string down to the list
        if isinstance(server_roles_list, str):
            server_roles_list = [item.strip()
                                 for item
                                 in re.split(r"\s+", server_roles_list.strip())
                                 if len(item) > 0]   # Eliminate multiple spaces
        if server_roles_list is not None:
            # Process the prefixes to determine whether add or remove
            # Resulting format [(remove?, "role"), ...]
            server_roles_list = [(item[0] == "-",                   # 1) Bool whether remove?
                                  item[1:]                          # 2) Removing the prefix +,-
                                  if item.startswith(("+", "-"))    # 2) If present
                                  else item)                        # 2) Else not
                                 for item
                                 in server_roles_list
                                 if len(item) > 0]                  # Ensure it is not empty
            for remove, role in server_roles_list:
                if remove and role in roles_list:
                    roles_list.remove(role)
                elif not remove and role not in roles_list:
                    roles_list.append(role)
                else:
                    role_message = ("+", "-")[remove] + role   # False = 0, True = 1
                    logger.info("FIXTURE[server_roles]: No change with role setting %s" %
                                role_message)
    elif 'server_roles_cfmedata' in fixtureconf:
        roles_list = cfme_data
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

    # Check whether we specified correct roles
    # Copy it to prevent excessive selenium querying
    # and we need also only the names
    possible_roles = [item.name for item in sst.server_roles]
    for role in roles_list:
        if role not in possible_roles:
            raise Exception("Role '%s' does not exist!" % role)

    # Set the roles!
    if sorted(sst.selected_server_role_names) != sorted(roles_list):
        sst.set_server_roles(roles_list)
        sst.save()
        sst._wait_for_results_refresh()
    else:
        logger.info('FIXTURE[server_roles]: Server roles already match configured fixture roles," +\
            " not changing server roles')

    # If this assert fails, check roles names for typos or other minor differences
    assert sorted(sst.selected_server_role_names) == sorted(roles_list)

    return sst.selected_server_role_names
