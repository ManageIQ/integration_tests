import pytest

from cfme import test_requirements
from cfme.exceptions import CandidateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.stack import Stack
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.web_ui import Table, Quadicon


pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    test_requirements.stack
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [EC2Provider])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope='module')


@pytest.yield_fixture(scope="module")
def stack(setup_provider_modscope, provider):
    stack = Stack(provider.data['provisioning']['stack'], provider=provider)
    stack.wait_for_appear()
    yield stack

    try:
        stack.delete()
    except Exception:
        pass


@pytest.mark.tier(3)
def test_security_group_link(stack):
    try:
        navigate_to(stack, 'RelationshipSecurityGroups')
    except CandidateNotFound:
        # Assert there is a non-clickable anchor
        assert sel.is_displayed(
            '//div[@id="stack_rel"]//a[@href="#" and normalize-space(.)="Security Groups (0)"]')
    else:
        # Navigation successful, stack had security groups
        assert sel.is_displayed(
            '//h1[contains(text(), "{} (All Security Groups)")]'.format(stack.name))


@pytest.mark.tier(3)
def test_parameters_link(stack):
    navigate_to(stack, 'RelationshipParameters')
    assert sel.is_displayed('//h1[contains(text(), "{} (Parameters)")]'.format(stack.name))


@pytest.mark.tier(3)
def test_outputs_link(stack):
    try:
        navigate_to(stack, 'RelationshipOutputs')
    except CandidateNotFound:
        # Assert there is a non-clickable anchor
        assert sel.is_displayed(
            '//div[@id="stack_rel"]//a[@href="#" and normalize-space(.)="Outputs (0)"]')
    else:
        assert sel.is_displayed('//h1[contains(text(), "{} (Outputs)")]'.format(stack.name))


@pytest.mark.tier(3)
def test_outputs_link_url(stack):
    try:
        navigate_to(stack, 'RelationshipOutputs')
    except CandidateNotFound:
        # Assert there is a non-clickable anchor
        assert sel.is_displayed(
            '//div[@id="stack_rel"]//a[@href="#" and normalize-space(.)="Outputs (0)"]')
    else:
        # Outputs is a table with clickable rows
        table = Table('//div[@id="list_grid"]//table[contains(@class, "table-selectable")]')
        table.click_row_by_cells({'Key': 'WebsiteURL'}, 'Key')
        assert sel.is_displayed_text("WebsiteURL")


@pytest.mark.tier(3)
def test_resources_link(stack):
    try:
        navigate_to(stack, 'RelationshipResources')
    except CandidateNotFound:
        # Assert there is a non-clickable anchor
        assert sel.is_displayed(
            '//div[@id="stack_rel"]//a[@href="#" and normalize-space(.)="Resources (0)"]')
    else:
        assert sel.is_displayed('//h1[contains(text(), "{} (Resources)")]'.format(stack.name))


@pytest.mark.tier(3)
@test_requirements.tag
def test_edit_tags(stack):
    stack.edit_tags("Cost Center *", "Cost Center 001")


@pytest.mark.tier(3)
def test_delete(stack, provider, request):
    stack.delete()
    navigate_to(stack, 'All')
    assert not sel.is_displayed(Quadicon(stack.name, stack.quad_name))
    request.addfinalizer(provider.refresh_provider_relationships)
