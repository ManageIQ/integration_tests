import pytest

from cfme.containers.provider import ContainersProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')]


@pytest.mark.polarion('CMP-10255')
@pytest.mark.uncollectif(lambda appliance, provider: appliance.version <= "5.9",
                         reason='Cockpit Feature is only available in 5.9 and greater')
@pytest.mark.parametrize('cockpit', [False, True], ids=['disabled', 'enabled'])
def test_cockpit_button_access(appliance, provider, cockpit, request):
    """ The test verifies the existence of cockpit "Web Console"
        button on master node, click the button if enabled, verify no errors are displayed.

    Polarion:
        assignee: None
        initialEstimate: None
    """

    request.addfinalizer(lambda: appliance.server.settings.disable_server_roles('cockpit_ws'))

    if cockpit:
        appliance.server.settings.enable_server_roles('cockpit_ws')
        wait_for(lambda: appliance.server_roles['cockpit_ws'] is True, delay=10, timeout=300)
    elif not cockpit:
        appliance.server.settings.disable_server_roles('cockpit_ws')
        wait_for(lambda: appliance.server_roles['cockpit_ws'] is False, delay=10, timeout=300)
    else:
        pytest.skip("Cockpit should be either enabled or disabled.")

    collection = appliance.collections.container_nodes
    nodes = collection.all()
    node = [node for node in nodes if 'master' in node.name][0]
    view = navigate_to(node, 'Details')

    if cockpit:
        appliance.server.browser.refresh()
        assert not view.toolbar.web_console.disabled
        view.toolbar.web_console.click()
        if provider.version < 3.7:
            assert view.is_displayed
            view.flash.assert_message("Feature not available/supported")
        else:
            webconsole = node.vm_console
            webconsole.switch_to_console()
            assert not view.is_displayed
            assert appliance.url in appliance.server.browser.url
            assert node.name in appliance.server.browser.url
            webconsole.close_console_window()
            assert view.is_displayed
            view.flash.assert_no_error()
    else:
        appliance.server.browser.refresh()
        assert view.toolbar.web_console.disabled
