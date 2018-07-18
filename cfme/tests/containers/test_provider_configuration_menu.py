import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.containers.provider import ContainersProvider
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]


@pytest.mark.polarion('CMP-9880')
def test_edit_selected_containers_provider(provider):
    '''Testing Configuration -> Edit... button functionality
    Step:
        In Providers summary page - click configuration
        menu and select "Edit this containers provider"
    Expected result:
        The user should be navigated to the container's basic information page.'''
    view = navigate_to(provider, 'Edit')
    assert view.is_displayed
    view.cancel.click()

def test_start_embedded_ansible(appliance):

    def monitor_container(appliance):
        appliance.collections.containers.all()

    # Enable embedded ansible
    args = ["embedded_ansible"]
    appliance.server.settings.enable_server_roles(*args)

    # Waiting for container to start
    assert wait_for(monitor_container, delay=30, timeout="10m"), "No ansible container started"