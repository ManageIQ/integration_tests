import pytest

from cfme import test_requirements
from cfme.containers.provider import ContainersProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider(gen_func=providers,
                         filters=[ProviderFilter(classes=[ContainersProvider],
                                                 required_flags=['cockpit'])],
                         scope='function'),
    test_requirements.containers
]


@pytest.mark.parametrize('cockpit', [False, True], ids=['disabled', 'enabled'])
def test_cockpit_button_access(appliance, provider, cockpit, request):
    """ The test verifies the existence of cockpit "Web Console"
        button on each node, click the button if enabled, verify no errors are displayed.

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
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

    for node in nodes:

        view = (navigate_to(node, 'Details', force=True) if node else
                pytest.skip("Could not determine node of {}".format(provider.name)))

        if cockpit:
            assert not view.toolbar.web_console.disabled
            view.toolbar.web_console.click()
            webconsole = node.vm_console
            webconsole.switch_to_console()
            assert not view.is_displayed
            assert node.name in appliance.server.browser.url
            webconsole.close_console_window()
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            assert view.toolbar.web_console.disabled
