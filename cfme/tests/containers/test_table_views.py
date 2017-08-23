from random import choice
import pytest

from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.web_ui import toolbar as tb
from cfme.configure.settings import DefaultView

from cfme.containers.container import Container
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.node import NodeCollection
from cfme.containers.provider import ContainersProvider
from cfme.containers.service import Service
from cfme.containers.replicator import Replicator
from cfme.containers.pod import Pod
from cfme.containers.route import Route
from cfme.containers.project import Project
from collections import OrderedDict


pytestmark = [pytest.mark.tier(2), pytest.mark.usefixtures('setup_provider')]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


VIEWS = ('Grid View', 'Tile View', 'List View')
# We're using OrderedDict in order to be able to set keys and values
# to DefaultView and keep the order of the LUT
objects_mapping = OrderedDict({  # <object> : <ui name>
    ContainersProvider: 'Containers Providers',
    Image: 'Images',
    ImageRegistry: 'Image Registries',
    Project: 'Projects',
    Route: 'Routes',
    NodeCollection: 'Nodes',
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
        navigate_to(obj, 'All', use_resetter=False)
        view = random_default_views[obj]
    if not tb.is_active(view):
        raise Exception("Failed to setup default view \"{}\" for {}"
                        .format(view, objects_mapping[obj]))


@pytest.mark.polarion('CMP-10570')
def test_table_views():
    for obj in objects_mapping.keys():
        navigate_to(obj, 'All')
        view = choice(VIEWS)
        tb.select(view)
        if not tb.is_active(view):
            raise Exception("Failed to set view \"{}\" For {}".format(view, obj.__name__))
