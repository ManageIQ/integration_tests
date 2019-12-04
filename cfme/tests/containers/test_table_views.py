import pytest

from cfme import test_requirements
from cfme.containers.provider import ContainersProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([ContainersProvider], scope='function'),
    test_requirements.containers
]

objects_mapping = {
    'Containers Providers': ContainersProvider,
    'Nodes': 'container_nodes',
    'Pods': 'container_pods',
    'Services': 'container_services',
    'Routes': 'container_routes',
    'Containers': 'containers',
    'Projects': 'container_projects',
    'Replicators': 'container_replicators',
    'Container Images': 'container_images',
    'Image Registries': 'container_image_registries',
}


@pytest.mark.parametrize('group_name', list(objects_mapping.keys()),
                         ids=["_".join(gp.split()) for gp in objects_mapping], scope="module")
@pytest.mark.parametrize('new_default_view', ['List View', 'Tile View', 'Grid View'],
                         ids=['List_View', 'Tile_View', 'Grid_View'])
def test_default_views(request, appliance, group_name, new_default_view):
    """
    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    collection_name = objects_mapping[group_name]
    default_views = appliance.user.my_settings.default_views
    orig_default = default_views.get_default_view(group_name)
    default_views.set_default_view(group_name, new_default_view)
    request.addfinalizer(lambda: default_views.set_default_view(group_name, orig_default))
    obj = (ContainersProvider if collection_name is ContainersProvider
           else getattr(appliance.collections, collection_name))
    view = navigate_to(obj, 'All', use_resetter=False)
    assert view.toolbar.view_selector.selected == new_default_view
    default_views.set_default_view(group_name, orig_default)


@pytest.mark.parametrize('container_obj', list(objects_mapping.keys()),
                         ids=["_".join(gp.split()) for gp in objects_mapping], scope="module")
@pytest.mark.parametrize('selected_view', ['List View', 'Tile View', 'Grid View'],
                         ids=['List_View', 'Tile_View', 'Grid_View'])
def test_table_views(appliance, selected_view, container_obj):
    """
    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    collection_name = objects_mapping[container_obj]
    obj = (ContainersProvider if collection_name is ContainersProvider
           else getattr(appliance.collections, collection_name))
    view = navigate_to(obj, 'All')
    view.toolbar.view_selector.select(selected_view)
    assert selected_view == view.toolbar.view_selector.selected, (
        f"Failed to set view {view} For {collection_name}"
    )
