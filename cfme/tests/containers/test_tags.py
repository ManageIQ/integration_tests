import pytest

from cfme.containers.provider import ContainersProvider


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([ContainersProvider], scope='function')
]

container_test_items = [
    'container_provider', 'container_projects', 'container_routes', 'container_services',
    'container_replicators', 'container_pods', 'container_nodes', 'container_volumes',
    'container_image_registries', 'container_images', 'container_templates']


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


@pytest.mark.parametrize('test_param', container_test_items, ids=[cti for cti in
                                                                  container_test_items])
@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_container_objects(soft_assert, test_param, appliance, provider, request, tag,
                               tag_place):
    """ Test for container items tagging action from list and details pages

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """

    obj_under_test = get_collection_entity(appliance=appliance, collection_name=test_param,
                                           provider=provider)

    obj_under_test.add_tag(tag=tag, details=tag_place)

    tags = obj_under_test.get_tags()

    assert any(
        object_tags.category.display_name == tag.category.display_name and
        object_tags.display_name == tag.display_name for object_tags in tags), (
        "{}: {} not in ({})".format(tag.category.display_name, tag.display_name, str(tags)))

    obj_under_test.remove_tag(tag=tag, details=tag_place)

    post_remove_tags = obj_under_test.get_tags()
    if post_remove_tags:
        for post_tags in post_remove_tags:
            soft_assert(
                not post_tags.category.display_name == tag.category.display_name and
                not post_tags.display_name == tag.display_name)
