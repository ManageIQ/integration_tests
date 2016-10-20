import pytest

from cfme.fixtures import pytest_selenium as sel
from cfme.cloud.stack import Stack
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from cfme.configure import settings  # NOQA
from cfme.web_ui import Table, Quadicon


pytestmark = [
    pytest.mark.ignore_stream("upstream"),
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['ec2'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope='module')


@pytest.fixture(scope="function")
def stack(setup_provider, provider, provisioning):
    return Stack(provisioning['stack'])


@pytest.mark.tier(3)
def test_security_group_link(stack):
    navigate_to(stack, 'RelationshipSecurityGroups')
    assert sel.is_displayed('//h1[contains(text(), "{} (All Security Groups)")]'.format(stack.name))


@pytest.mark.tier(3)
def test_parameters_link(stack):
    navigate_to(stack, 'RelationshipParameters')
    assert sel.is_displayed('//h1[contains(text(), "{} (Parameters)")]'.format(stack.name))


@pytest.mark.tier(3)
def test_outputs_link(stack):
    navigate_to(stack, 'RelationshipOutputs')
    assert sel.is_displayed('//h1[contains(text(), "{} (Outputs)")]'.format(stack.name))


@pytest.mark.tier(3)
def test_outputs_link_url(stack):
    navigate_to(stack, 'RelationshipOutputs')
    # Outputs is a table with clickable rows
    table = Table('//div[@id="list_grid"]//table[contains(@class, "table-selectable")]')
    table.click_row_by_cells({'Key': 'WebsiteURL'}, 'Key')
    assert sel.is_displayed_text("WebsiteURL")


@pytest.mark.tier(3)
def test_resources_link(stack):
    navigate_to(stack, 'RelationshipResources')
    assert sel.is_displayed('//h1[contains(text(), "{} (Resources)")]'.format(stack.name))


@pytest.mark.tier(3)
def test_edit_tags(stack):
    stack.edit_tags("Cost Center *", "Cost Center 001")


@pytest.mark.tier(3)
def test_delete(stack, provider, request):
    stack.delete()
    navigate_to(stack, 'All')
    assert not sel.is_displayed(Quadicon(stack.name, stack.quad_name))
    request.addfinalizer(provider.refresh_provider_relationships)
