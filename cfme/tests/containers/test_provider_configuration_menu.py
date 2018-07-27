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


def test_ocp_operator_out_of_the_box(appliance):

    roles_collection = appliance.collections.roles
    view = navigate_to(roles_collection, "All")
    role_name_prefix = "container_operator"
    is_role_found = bool(filter(lambda row: role_name_prefix in row.name.text.lower(),
                                view.table.rows()))

    assert is_role_found, "No {role} found".format(role=role_name_prefix)
