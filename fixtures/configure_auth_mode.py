import pytest
from unittestzero import Assert


@pytest.fixture  # IGNORE:E1101
def configure_auth_mode(cnf_configuration_pg, cfme_data):
    '''Configure authentication mode'''
    server_data = cfme_data.data['ldap_server']
    auth_pg = cnf_configuration_pg.click_on_settings().click_on_current_server_tree_node().click_on_authentication_tab()
    Assert.true(auth_pg.is_the_current_page)
    if auth_pg.current_auth_mode != server_data['mode']:
        auth_pg.ldap_server_fill_data(**server_data)
        if server_data['get_groups'] and server_data['mode'] != "database":
            auth_pg.validate()
            Assert.contains("LDAP Settings validation was successful", auth_pg.flash.message, "Validate flash message did not match")
        auth_pg = auth_pg.save()
        Assert.contains("Authentication settings saved", auth_pg.flash.message, "Auth page save flash message did not match")
