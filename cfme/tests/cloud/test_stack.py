import pytest

from widgetastic_manageiq import Table

from cfme import test_requirements
from cfme.exceptions import CandidateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    test_requirements.stack,
    pytest.mark.provider([EC2Provider], scope='module')
]


@pytest.yield_fixture(scope="module")
def stack(setup_provider_modscope, provider, appliance):
    collection = appliance.collections.stacks
    stack = collection.instantiate(provider.data['provisioning']['stacks'][0], provider=provider)
    stack.wait_for_exists()
    yield stack

    try:
        stack.delete()
    except Exception:
        pass


@pytest.mark.tier(3)
def test_security_group_link(stack):
    try:
        view = navigate_to(stack, 'RelationshipSecurityGroups')
    except CandidateNotFound:
        # Assert that the item in the menu is disabled
        view = navigate_to(stack, 'Details')
        assert view.sidebar.relationships.nav.is_disabled('Security Groups (0)')
    else:
        # Navigation successful, stack had security groups
        assert view.is_displayed
        assert view.entities.title.text == '{} (Security Groups)'.format(stack.name)


@pytest.mark.tier(3)
def test_parameters_link(stack):
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
def test_outputs_link_url(stack):
    try:
        view = navigate_to(stack, 'RelationshipOutputs')
    except CandidateNotFound:
        # Assert there is a non-clickable anchor
        view = navigate_to(stack, 'Details')
        assert view.sidebar.relationships.nav.is_disabled('Outputs (0)')
    else:
        # Outputs is a table with clickable rows
        # TODO: Need to come back to this one
        table = Table('//div[@id="list_grid"]//table[contains(@class, "table-selectable")]')
        table.click_row_by_cells({'Key': 'WebsiteURL'}, 'Key')
        assert sel.is_displayed_text("WebsiteURL")


@pytest.mark.tier(3)
def test_resources_link(stack):
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
def test_edit_tags(stack):
    stack.add_tag("Cost Center *", "Cost Center 001")


@pytest.mark.tier(3)
def test_delete(stack, provider, request):
    stack.delete()
    assert not stack.exists
    request.addfinalizer(provider.refresh_provider_relationships)


@pytest.mark.tier(3)
def test_collection_delete(provider, setup_provider_modscope, appliance):
    collection = appliance.collections.stacks

    stack1 = collection.instantiate(provider.data['provisioning']['stacks'][0], provider=provider)
    stack2 = collection.instantiate(provider.data['provisioning']['stacks'][1], provider=provider)

    stack1.wait_for_exists()
    stack2.wait_for_exists()

    collection.delete(stack1, stack2)
