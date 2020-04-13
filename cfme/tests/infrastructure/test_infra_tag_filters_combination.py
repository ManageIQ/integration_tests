import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update

pytestmark = [
    test_requirements.tag, pytest.mark.tier(2),
    pytest.mark.provider(
        classes=[InfraProvider],
        required_fields=[
            'datacenters',
            'clusters'
        ],
        selector=ONE
    ),
    pytest.mark.usefixtures('setup_provider')
]

test_items = [
    ('clusters', None),
    ('infra_vms', 'ProviderVms'),
    ('infra_templates', 'ProviderTemplates')
]


@pytest.fixture(params=test_items, ids=[collection_type for collection_type, _ in test_items],
                scope='function')
def testing_vis_object(request, provider, appliance):
    """ Fixture creates class object for tag visibility test

    Returns: class object of certain type
    """
    collection_name, destination = request.param
    collection = getattr(appliance.collections, collection_name)
    view = navigate_to(provider, destination) if destination else navigate_to(collection, 'All')
    names = view.entities.entity_names
    if not names:
        pytest.skip(f"No content found for test of {collection}")

    return collection.instantiate(name=names[0], provider=provider)


@pytest.fixture(scope='function')
def group_tag_datacenter_combination(group_with_tag, provider):
    with update(group_with_tag):
        group_with_tag.host_cluster = ([provider.data['name'],
                                        provider.data['datacenters'][0]], True)


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

    Polarion:
        assignee: prichard
        casecomponent: Tagging
        initialEstimate: 1/8h
    """
    check_item_visibility(testing_vis_object, visibility)
