import pytest

from cfme.containers.provider import ContainersProvider


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([ContainersProvider], scope='function')
]

container_test_items = [
    ('container_provider'),
    ('container_projects'),
    ('container_routes'),
    ('container_services'),
    ('container_replicators'),
    ('container_pods'),
    ('container_nodes'),
    ('container_volumes'),
    ('container_image_registries'),
    ('container_images'),
    ('container_templates')
]


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
    if all_entities:
        selected_entity = all_entities[0]
    else:
        pytest.skip("No content found for test")
    for klass in [item_collection]:
        d = {}
        for arg in ['name', 'project_name', 'host', 'id', 'provider']:
            if arg in [att.name for att in klass.ENTITY.__attrs_attrs__]:
                d[arg] = getattr(selected_entity, arg, None)
        return item_collection.instantiate(**d)


def _tag_cleanup(test_item, tag):
    """
        Clean Up Tags

        Args
            test_item: The OpenShift object under test
            tag: Generated tag object
        Returns:
            Boolean True or False
    """
    tags = test_item.get_tags()
    if tags:
        result = [
            not object_tags.category.display_name == tag.category.display_name and
            not object_tags.display_name == tag.display_name for object_tags in tags
        ]
        if not all(result):
            test_item.remove_tag(tag=tag)
    else:
        result = True
    return result


@pytest.fixture(params=container_test_items, ids=([item[0] for item in container_test_items]),
                scope='function')
def container_test_item(request, appliance, provider):
    collection_name = request.param
    return get_collection_entity(
        appliance, collection_name, provider)


@pytest.fixture(scope='function')
def tagging_check(tag):

    def _tagging_check(test_item, tag_place):
        """ Check if tagging is working
            1. Add tag
            2. Check assigned tag on details page
            3. Remove tag
            4. Check tag unassigned on details page
        """
        _tag_cleanup(test_item, tag)
        test_item.add_tag(tag=tag, details=tag_place)
        tags = test_item.get_tags()
        assert any(
            object_tags.category.display_name == tag.category.display_name and
            object_tags.display_name == tag.display_name for object_tags in tags), (
            "{}: {} not in ({})".format(tag.category.display_name, tag.display_name, str(tags)))

        test_item.remove_tag(tag=tag, details=tag_place)
        assert _tag_cleanup(test_item, tag)

    return _tagging_check


@pytest.mark.polarion('CMP-10837')
@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_container_objects(tagging_check, container_test_item, tag_place):
    """ Test for container items tagging action from list and details pages

    Polarion:
        assignee: None
        initialEstimate: None
    """
    tagging_check(container_test_item, tag_place)
