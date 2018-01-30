from random import choice
from collections import OrderedDict

import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.configure.settings import DefaultView
from cfme.containers.provider import ContainersProvider


pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([ContainersProvider], scope='function')
]


VIEWS = ('Grid View', 'Tile View', 'List View')
# We're using OrderedDict in order to be able to set keys and values
# to DefaultView and keep the order of the LUT
objects_mapping = OrderedDict({  # <object> : <ui name>
    ContainersProvider: 'Containers Providers',
    'container_images': 'Container Images',
    'container_image_registries': 'Image Registries',
    'container_projects': 'Projects',
    'container_routes': 'Routes',
    'container_nodes': 'Nodes',
    'container_pods': 'Pods',
    'container_services': 'Services',
    'containers': 'Containers',
    'container_replicators': 'Replicators'
})


@pytest.yield_fixture(scope='function')
def random_default_views():
    """This fixture setup random default views for container objects.
    Revert the default views to the original on exit"""
    # Collecting the original default views and Generating random views LUT for test:
    original_default_views, tested_default_views = OrderedDict(), OrderedDict()
    for collection_name, ui_name in objects_mapping.items():
        original_default_views[collection_name] = DefaultView.get_default_view(ui_name)
        tested_default_views[collection_name] = choice(VIEWS)
    DefaultView.set_default_view(list(objects_mapping.values()), list(tested_default_views.values()))
    yield tested_default_views
    # setting back the default views to the original state:
    DefaultView.set_default_view(list(objects_mapping.values()), list(original_default_views.values()))


@pytest.mark.polarion('CMP-10568')
def test_default_views(appliance, random_default_views):
    for collection_name in objects_mapping.keys():
        obj = (ContainersProvider if collection_name is ContainersProvider
               else getattr(appliance.collections, collection_name))
        view = navigate_to(obj, 'All', use_resetter=False)
        assert (random_default_views[collection_name].lower() ==
                view.toolbar.view_selector.selected.lower()), (
            "Failed to setup default view \"{}\" for {}".format(
                view, objects_mapping[collection_name])
        )


@pytest.mark.polarion('CMP-10570')
def test_table_views(appliance):
    for collection_name in objects_mapping.keys():
        obj = (ContainersProvider if collection_name is ContainersProvider
               else getattr(appliance.collections, collection_name))
        view = navigate_to(obj, 'All')
        view_to_select = choice(VIEWS)
        view.toolbar.view_selector.select(view_to_select)
        assert view_to_select.lower() == view.toolbar.view_selector.selected.lower(), (
            "Failed to set view \"{}\" For {}".format(view, collection_name)
        )
