import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.containers.provider import ContainersProvider
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]


def get_ansible_container_name(appliance):
    return filter(lambda container: "ansible" in container.name,
                  appliance.collections.containers.all())


@pytest.fixture
def get_old_ansible_containers_name(appliance):
    return get_ansible_container_name(appliance)


@pytest.yield_fixture
def disable_embedded_ansible(appliance):
    yield
    args = ["embedded_ansible"]
    appliance.server.settings.disable_server_roles(*args)


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
    """
    This test checks that the container oprator role is available out-of_the_box
    Steps:
     1. Navigate to  Administration | EVM (on the right upper corner)--> Configuration
     2. In the new page on the left menu select Access Control --> roles
     3. Search for container operator role
    """

    # Navigate to all roles page
    roles_collection = appliance.collections.roles
    view = navigate_to(roles_collection, "All")

    # Search for the required role
    role_name_prefix = "container_operator"
    is_role_found = bool(filter(lambda row: role_name_prefix in row.name.text.lower(),
                                view.table.rows()))

    # validate the role exist out-of-the-box
    assert is_role_found, "No {role} found".format(role=role_name_prefix)


def test_start_embedded_ansible(appliance, get_old_ansible_containers_name,
                                disable_embedded_ansible):
    """
    In this test ansible embedded is tested
    Tests steps:
        * Enable ansible embadded
        * Wait for ansible container to start
    """
    def is_ansible_container_created(appliance):
        return bool(set(get_ansible_container_name(appliance)) - set(old_conainers_name))
    old_conainers_name = get_old_ansible_containers_name
    # Enable embedded ansible
    args = ["embedded_ansible"]
    appliance.server.settings.enable_server_roles(*args)

    # Waiting for container to start
    assert wait_for(is_ansible_container_created, [appliance], delay=30, timeout="15m"), (
        "No ansible container started")
