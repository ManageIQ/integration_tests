import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.fixtures.provider import setup_one_or_skip
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.providers import ProviderFilter
from cfme.utils.update import update


pytestmark = [test_requirements.tag, pytest.mark.tier(2)]

test_items = [
    ('clusters', None, None),
    ('infra_vms', None, 'ProviderVms'),
    ('infra_templates', None, 'ProviderTemplates')
]


@pytest.fixture(scope='module')
def a_provider(request):
    prov_filter = ProviderFilter(classes=[InfraProvider],
                                 required_fields=['datacenters', 'clusters'])
    return setup_one_or_skip(request, filters=[prov_filter])


@pytest.fixture(params=test_items, ids=[collection_type for collection_type, _, _ in test_items],
                scope='function')
def testing_vis_object(request, a_provider, appliance):
    """ Fixture creates class object for tag visibility test

    Returns: class object of certain type
    """
    collection_name, param_class, destination = request.param
    if not param_class:
        param_class = getattr(appliance.collections, collection_name)
    view = navigate_to(a_provider, destination) if destination else navigate_to(param_class, 'All')
    names = view.entities.entity_names
    if not names:
        pytest.skip("No content found for test")
    try:
        return param_class.instantiate(name=names[0], provider=a_provider)
    except AttributeError:
        return param_class(name=names[0], provider=a_provider)


@pytest.fixture(scope='module')
def group_tag_datacenter_combination(group_with_tag, a_provider):
    with update(group_with_tag):
        group_with_tag.host_cluster = ([a_provider.data['name'],
                                        a_provider.data['datacenters'][0]], True)


@pytest.mark.meta(blockers=[BZ(1533391, forced_streams=["5.9", "upstream"])])
@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'not_visible'])
def test_tagvis_tag_datacenter_combination(testing_vis_object, group_tag_datacenter_combination,
                                check_item_visibility, visibility):
    """ Tests template visibility with combination  of tag and selected

        datacenter filters in the group
        Prerequisites:
            Catalog, tag, role, group and restricted user should be created

        Steps:
            1. As admin add tag
            2. Login as restricted user, item is visible for user
            3. As admin remove tag
            4. Login as restricted user, iten is not visible for user
    """
    check_item_visibility(testing_vis_object, visibility)
