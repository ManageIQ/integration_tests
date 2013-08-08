import pytest
from unittestzero import Assert


@pytest.fixture(scope="module",  # IGNORE:E1101
                params=["default"])
def roles(request, cfme_data):
    param = request.param
    return cfme_data.data['server_roles'][param]


@pytest.mark.destructive
@pytest.mark.usefixtures("maximized")
def test_edit_server_roles(configuration_pg, roles):
    '''Set roles for appliance
    '''
    server_pg = configuration_pg.click_on_settings().\
        click_on_current_server_tree_node().click_on_server_tab()
    server_pg.set_server_roles(roles)
    server_pg.save()
    Assert.contains(
        'Configuration settings saved',
        server_pg.flash.message,
        'Flash save message does not match')

@pytest.mark.usefixtures("maximized")
def test_verify_server_roles(configuration_pg, roles):
    '''Verify roles assigned correctly
    '''
    server_pg = configuration_pg.click_on_settings().\
        click_on_current_server_tree_node().click_on_server_tab()
    for r in server_pg.server_roles:
        if r.is_selected:
            Assert.true(r.name in roles, 
                "Role '%s' is selected but should not be" % r.name)
        else:
            Assert.true(r.name not in roles, 
                "Role '%s' is not selected but should be" % r.name)
