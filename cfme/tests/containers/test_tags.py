import pytest

from cfme import test_requirements
from cfme.containers.provider import ContainersProvider
from cfme.utils.blockers import BZ


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([ContainersProvider], scope='function'),
    test_requirements.containers
]

container_test_items = [
    'container_provider', 'container_projects', 'container_routes', 'container_services',
    'container_replicators', 'container_pods', 'container_nodes', 'container_volumes',
    'container_image_registries', 'container_images', 'container_templates']


bz_1665284_test_items = ["container_provider", "container_projects"]


def get_collection_entity(appliance, collection_name, provider):
    """
        Instantiating OpenShift Collection Object

        Args
            appliance: The appliance under test
            collection_name: The name of the collection object under test
            provider: The provider under test
        Returns:
            The instantiated collection object
    """

    if collection_name in ['container_provider']:
        return provider
    item_collection = getattr(appliance.collections, collection_name)
    all_entities = item_collection.all()
    for entity in all_entities:
        if entity.exists:
            selected_entity = entity
            break
    else:
        pytest.skip("No content found for test")
    for klass in [item_collection]:
        d = {}
        for arg in ['name', 'project_name', 'host', 'id', 'provider']:
            if arg in [att.name for att in klass.ENTITY.__attrs_attrs__]:
                d[arg] = getattr(selected_entity, arg, None)
        return item_collection.instantiate(**d)


def verify_tags(obj_under_test, tag, details, dashboard):

    obj_under_test.add_tag(tag=tag, details=details, dashboard=dashboard)

    tags = obj_under_test.get_tags()

    assert any(
        object_tags.category.display_name == tag.category.display_name and
        object_tags.display_name == tag.display_name for object_tags in tags), (
        "{tag_cat_name}: {tag_name} not in ({tags})"
            .format(tag_cat_name=tag.category.display_name, tag_name=tag.display_name,
                    tags=str(tags)))

    obj_under_test.remove_tag(tag=tag, details=details)

    post_remove_tags = obj_under_test.get_tags()
    if post_remove_tags:
        for post_tags in post_remove_tags:
            assert(
                post_tags.category.display_name != tag.category.display_name and
                post_tags.display_name != tag.display_name)


@pytest.mark.parametrize('test_param', container_test_items)
@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_container_objects(test_param, appliance, provider, tag, tag_place):
    """ Test for container items tagging action from list and details pages

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """

    obj_under_test = get_collection_entity(appliance=appliance, collection_name=test_param,
                                           provider=provider)

    verify_tags(obj_under_test=obj_under_test, tag=tag, details=tag_place, dashboard=False)


@pytest.mark.parametrize('test_param', bz_1665284_test_items)
@pytest.mark.meta(
    blockers=[BZ(1667178, forced_streams=['5.10'],
                 unblock=lambda test_param: test_param != "container_provider")])
def test_tag_container_objects_dashboard_view(test_param, appliance, provider, tag):
    """ Test for BZ 1665284: Tagging: Unable to edit tag from container provider or container
    project dashboard view

       Polarion:
           assignee: juwatts
           casecomponent: Containers
           caseimportance: high
           initialEstimate: 1/6h
       """

    obj_under_test = get_collection_entity(appliance=appliance, collection_name=test_param,
                                           provider=provider)

    verify_tags(obj_under_test=obj_under_test, tag=tag, details=False, dashboard=True)
