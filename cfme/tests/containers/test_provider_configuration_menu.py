import pytest

from cfme import test_requirements
from cfme.containers.provider import ContainersProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function'),
    test_requirements.containers
]


def check_buttons_status(view, pause_option, resume_option):

    # get both buttons status
    pause_option_status = view.toolbar.configuration.item_enabled(pause_option)
    resume_option_status = view.toolbar.configuration.item_enabled(resume_option)

    # ensure only one of the buttons available at the time
    if pause_option_status and resume_option_status:
        return False, "Both pause and resume buttons are active at the same time"
    if not (pause_option_status or resume_option_status):
        return False, "Both pause and resume buttons are disabled at the same time"
    return True, None


def test_edit_selected_containers_provider(provider):
    """
    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
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

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """

    # Navigate to all roles page
    roles_collection = appliance.collections.roles
    view = navigate_to(roles_collection, "All")

    # Search for the required role
    role_name_prefix = "container_operator"
    is_role_found = bool([row for row
                          in view.table.rows()
                          if role_name_prefix in row.name.text.lower()])

    # validate the role exist out-of-the-box
    assert is_role_found, "No {role} found".format(role=role_name_prefix)


def test_pause_and_resume_provider(provider):
    """
    Basic testing for pause and resume for a container provider
    Tests steps:
        1. Navigate to provider page
        2. Validate buttons status are as expected
        3. Pause the provider
        4. Validate the button status
        5. Validate the provider marked as paused
        6. Resume the provider
        7. Validate button status
        8. Validate the provider marked as running
    The test based on BZ1516292

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """

    view = navigate_to(provider, "Details")
    buttn_status, error_msg = (
        check_buttons_status(view, provider.pause_provider_text, provider.resume_provider_text))

    assert buttn_status, error_msg

    # pause the provider
    view.toolbar.configuration.item_select(provider.pause_provider_text, handle_alert=True)

    view.browser.refresh()
    buttn_status, error_msg = (
        check_buttons_status(view, provider.pause_provider_text, provider.resume_provider_text))

    assert buttn_status, error_msg

    assert view.entities.summary("Status").get_text_of("Data Collection").lower() == "paused", (
        "Provider did not pause after pause request")

    # resume the provider
    view.toolbar.configuration.item_select(provider.resume_provider_text, handle_alert=True)

    view.browser.refresh()
    buttn_status, error_msg = (
        check_buttons_status(view, provider.pause_provider_text, provider.resume_provider_text))
    assert buttn_status, error_msg

    assert view.entities.summary("Status").get_text_of("Data Collection").lower() == "running", (
        "Provider did not resumed after pause request")
