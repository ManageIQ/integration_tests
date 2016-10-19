# the test verifies functionality
# of different views such as grid view, tile view
# and list view
import pytest

from cfme.containers.container import Container
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.node import Node
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version
from cfme.containers.replicator import Replicator
from cfme.containers.pod import Pod


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.5"),
    pytest.mark.usefixtures('setup_provider')]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


def test_pods_views():
    navigate_to(Pod, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Pods grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Pods tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Pods list view setting failed"


def test_replicators_views():
    navigate_to(Replicator, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Replicators grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Replicators tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Replicators list view setting failed"


def test_containers_views():
    navigate_to(Container, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Containers grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Containers tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Containers list view setting failed"


def test_services_views():
    sel.force_navigate('containers_services')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Services grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Services tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Services list view setting failed"


def test_nodes_views():
    navigate_to(Node, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Nodes grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Nodes tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Nodes list view setting failed"


def test_images_views():
    navigate_to(Image, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Images grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Images tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Images list view setting failed"


def test_imageregistry_views():
    navigate_to(ImageRegistry, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Images grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Images tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Images list view setting failed"
