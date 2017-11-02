import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.containers.provider import ContainersProvider


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


@pytest.mark.polarion('CMP-9881')
def test_remove_selected_containers_provider(provider):
    '''Testing Configuration -> Remove... button functionality
    Step:
        In Providers summary page - click configuration menu and select
        "Remove this container provider from VMDB"
    Expected result:
        The user should be shown a warning message following a
        success message that the provider has been deleted from VMDB.'''
    provider.delete(cancel=False)
    # The assertion of success is inside the delete function
