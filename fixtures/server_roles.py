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
def server_roles(request, cfme_data, home_page_logged_in):
    """Set the server roles based on a list of roles attached to the test using this fixture

    Usage examples:

        Pass the desired roles in to the "server_roles_set" decorator:

        from fixtures.roles import server_roles_set
        @server_roles_set('database_operations', 'event', 'user_interface', 'web_services')
        def test_appliance_roles(server_roles):
            assert len(server_roles) == 4

        Roles can be pulled from the cfme_data fixture using yaml selectors,
        which will do a 'set' with the list of roles found at the target path:

        from fixtures.roles import server_roles_cfme_data
        @server_roles_cfme_data('level1', 'sublevel2'))
        def test_appliance_roles(server_roles):
            assert len(server_roles) == 3

        Which corresponds to this yaml layout:

        level1:
            sublevel2:
                - database_operations
                - user_interface
                - web_services

        To ensure the appliance has the default roles:
        from fixtures.roles import server_roles_set, default_roles
        @server_roles_set(*default_roles)
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

    try:
        roles_dict = request.node.obj._fixture_server_roles
    except AttributeError:
        raise Exception('server_roles config not found on test callable')

    # Input validation and cleanup; this fixture can work a few different ways, so make sure everything
    # is sane (no conflicting args, cfme_data lookup works, etc) before taking any action
    if 'cfme_data_selectors' in roles_dict and 'set' in roles_dict:
        raise Exception('Cannot have "set" and "cfme_data_selectors" in roles fixture dict')
    elif 'cfme_data_selectors' in roles_dict:
        # Roles enumerated in cfme_data, overwrite all roles with what's there using 'set'
        roles_list = cfme_data.data
        for selector in roles_dict['cfme_data_selectors']:
            roles_list = roles_list[selector]
    elif 'set' in roles_dict:
        roles_list = roles_dict['set']
    else:
        raise Exception('No roles defined to set with roles fixture')

    # Deselecting the user interface role is really un-fun, and is
    # counterproductive in the middle of user interface testing.
    if 'user_interface' not in roles_list:
        raise Exception('Refusing to remove the user_interface role')

    # Nav to the settings tab
    conf_pg = home_page_logged_in.header.site_navigation_menu("Configuration").\
        sub_navigation_menu("Configuration").click()
    settings_pg = conf_pg.click_on_settings()
    server_settings_pg = settings_pg.click_on_current_server_tree_node()
    # sst is a configuration_subpages.settings_subpages.server_settings_subpages.server_settings_tab.ServerSettingsTab
    sst = server_settings_pg.click_on_server_tab()

    # Set the roles!
    if sorted(sst.selected_server_role_names) != sorted(roles_list):
        sst.set_server_roles(roles_list)
        sst.save()
        sst._wait_for_results_refresh()
    else:
        logger.info('Server roles already match configured fixture roles, not changing server roles')

    # If this gets thrown, check roles names for typos or other minor differences
    Assert.equal(sorted(sst.selected_server_role_names), sorted(roles_list))

    return sst.selected_server_role_names


###
# Decorators! See usage in the server_roles fixture docs
###

def server_roles_set(*roles):
    roles_dict = {'set': list(roles)}
    def wrapper(func):
        func._fixture_server_roles = roles_dict
        return func
    return wrapper

def server_roles_cfme_data(*cfme_data_selectors):
    roles_dict = {'cfme_data_selectors': list(cfme_data_selectors)}
    def wrapper(func):
        func._fixture_server_roles = roles_dict
        return func
    return wrapper

