import pytest
from unittestzero import Assert

from fixtures.navigation import cnf_configuration_pg
from utils.conf import cfme_data


@pytest.yield_fixture(scope='module')  # IGNORE:E1101
def configure_ldap_auth_mode():
    '''Configure authentication mode'''
    server_data = cfme_data['ldap_server']
    auth_pg = cnf_configuration_pg().click_on_settings()\
        .click_on_current_server_tree_node()\
        .click_on_authentication_tab()
    if auth_pg.current_auth_mode != server_data['mode']:
        auth_pg.ldap_server_fill_data(**server_data)
        if server_data['get_groups'] and server_data['mode'] != "database":
            auth_pg.validate()
            Assert.contains("LDAP Settings validation was successful",
                            auth_pg.flash.message,
                            "Validate flash message did not match")
        auth_pg = auth_pg.save()
        Assert.contains("Authentication settings saved",
                        auth_pg.flash.message,
                        "Auth page save flash message did not match")

    yield

    auth_pg = cnf_configuration_pg().click_on_settings()\
        .click_on_current_server_tree_node()\
        .click_on_authentication_tab()
    auth_pg.current_auth_mode = 'database'
    auth_pg.save()
