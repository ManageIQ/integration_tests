import pytest
from widgetastic_patternfly import CandidateNotFound

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.stack import StackOutputsDetails
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    test_requirements.stack,
    pytest.mark.provider([EC2Provider], scope='module')
]


@pytest.fixture(scope="module")
def stack(setup_provider_modscope, provider, appliance):
    collection = appliance.collections.cloud_stacks
    for stack_name in provider.data.provisioning.stacks:
        stack = collection.instantiate(stack_name, provider=provider)
        try:
            stack.wait_for_exists()
            return stack
        except Exception:
            pass
    pytest.skip("No available stacks found for test")


@pytest.mark.tier(3)
def test_security_group_link(stack):
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Stack
    """
    try:
        view = navigate_to(stack, 'RelationshipSecurityGroups')
    except CandidateNotFound:
        # Assert that the item in the menu is disabled
        view = navigate_to(stack, 'Details')
        assert view.sidebar.relationships.nav.is_disabled('Security Groups (0)')
    else:
        # Navigation successful, stack had security groups
        assert view.is_displayed
        assert view.entities.title.text == '{} (All Security Groups)'.format(stack.name)


@pytest.mark.tier(3)
def test_parameters_link(stack):
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/8h
        casecomponent: Stack
    """
    try:
        view = navigate_to(stack, 'RelationshipParameters')
    except CandidateNotFound:
        # Assert that the item in the menu is disabled
        view = navigate_to(stack, 'Details')
        assert view.sidebar.relationships.nav.is_disabled('Parameters (0)')
    else:
        # Navigation successful, stack had parameters
        assert view.is_displayed
        assert view.entities.title.text == '{} (Parameters)'.format(stack.name)


@pytest.mark.tier(3)
def test_outputs_link(stack):
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Stack
    """
    try:
        view = navigate_to(stack, 'RelationshipOutputs')
    except CandidateNotFound:
        # Assert there is a non-clickable anchor
        view = navigate_to(stack, 'Details')
        assert view.sidebar.relationships.nav.is_disabled('Outputs (0)')
    else:
        assert view.is_displayed
        assert view.entities.title.text == '{} (Outputs)'.format(stack.name)


@pytest.mark.tier(3)
def test_outputs_link_url(appliance, stack):
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Stack
    """
    try:
        view = navigate_to(stack, 'RelationshipOutputs')
    except CandidateNotFound:
        # Assert there is a non-clickable anchor
        view = navigate_to(stack, 'Details')
        assert view.sidebar.relationships.nav.is_disabled('Outputs (0)')
    else:
        # Outputs is a table with clickable rows
        key_value = view.entities.outputs[0].key.text
        view.entities.outputs[0].click()
        view = appliance.browser.create_view(StackOutputsDetails)
        assert view.title.text == key_value


@pytest.mark.tier(3)
def test_resources_link(stack):
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Stack
    """
    try:
        view = navigate_to(stack, 'RelationshipResources')
    except CandidateNotFound:
        # Assert there is a non-clickable anchor
        view = navigate_to(stack, 'Details')
        assert view.sidebar.relationships.nav.is_disabled('Resources (0)')
    else:
        assert view.is_displayed is True
        assert view.entities.title.text == '{} (Resources)'.format(stack.name)


@pytest.mark.tier(3)
@test_requirements.tag
def test_edit_tags_stack(request, stack):
    """
    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: low
        initialEstimate: 1/8h
    """
    added_tag = stack.add_tag()
    request.addfinalizer(lambda: stack.remove_tag(added_tag))


@pytest.mark.tier(3)
def test_delete_stack(stack, provider, request):
    """
    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Stack
    """
    stack.delete()
    assert not stack.exists
    request.addfinalizer(provider.refresh_provider_relationships)


@pytest.mark.tier(3)
def test_collection_delete(provider, setup_provider_modscope, appliance):
    """
    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Stack
    """
    collection = appliance.collections.cloud_stacks

    stack1 = collection.instantiate(provider.data['provisioning']['stacks'][0], provider=provider)
    stack2 = collection.instantiate(provider.data['provisioning']['stacks'][1], provider=provider)

    stack1.wait_for_exists()
    stack2.wait_for_exists()

    collection.delete(stack1, stack2)
