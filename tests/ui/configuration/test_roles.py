import pytest
from unittestzero import Assert


@pytest.fixture(scope="module",  # IGNORE:E1101
                params=["default"])
def roles(request, cfme_data):
    param = request.param
    return cfme_data.data['roles'][param]


@pytest.mark.destructive
@pytest.mark.usefixtures("maximized")
def test_edit_roles(configuration_pg, roles):
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
