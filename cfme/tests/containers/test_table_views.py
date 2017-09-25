from random import choice
from collections import OrderedDict

import pytest

from cfme.modeling.base import BaseCollection
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.configure.settings import DefaultView
from cfme.containers.container import Container
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.provider import ContainersProvider
from cfme.containers.service import Service
from cfme.containers.replicator import Replicator
from cfme.containers.pod import Pod
from cfme.containers.route import Route
from cfme.containers.project import Project


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
    Image: 'Container Images',
    ImageRegistry: 'Image Registries',
    Project: 'Projects',
    Route: 'Routes',
    # TODO Add Node back into the list when other classes are updated to use WT views and widgets.
    # NodeCollection: 'Nodes',
    Pod: 'Pods',
    Service: 'Services',
    Container: 'Containers',
    Replicator: 'Replicators'
})


@pytest.yield_fixture(scope='function')
def random_default_views():
    """This fixture setup random default views for container objects.
    Revert the default views to the original on exit"""
    # Collecting the original default views and Generating random views LUT for test:
    original_default_views, tested_default_views = OrderedDict(), OrderedDict()
    for obj, ui_name in objects_mapping.items():
        original_default_views[obj] = DefaultView.get_default_view(ui_name)
        tested_default_views[obj] = choice(VIEWS)
    DefaultView.set_default_view(objects_mapping.values(), tested_default_views.values())
    yield tested_default_views
    # setting back the default views to the original state:
    DefaultView.set_default_view(objects_mapping.values(), original_default_views.values())


@pytest.mark.polarion('CMP-10568')
def test_default_views(random_default_views):
    for obj in objects_mapping.keys():
        view = navigate_to(obj, 'All', use_resetter=False)
        assert random_default_views[obj].lower() == view.toolbar.view_selector.selected.lower(), (
            "Failed to setup default view \"{}\" for {}".format(view, objects_mapping[obj])
        )


@pytest.mark.polarion('CMP-10570')
def test_table_views(appliance):
    for obj in objects_mapping.keys():
        if isinstance(obj, BaseCollection):
            obj = appliance.get(obj)
        view = navigate_to(obj, 'All')
        view_to_select = choice(VIEWS)
        view.toolbar.view_selector.select(view_to_select)
        assert view_to_select.lower() == view.toolbar.view_selector.selected.lower(), (
            "Failed to set view \"{}\" For {}".format(view, obj.__name__)
        )
