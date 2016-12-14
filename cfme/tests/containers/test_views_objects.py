import pytest

from cfme.containers.container import Container
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.node import Node
from cfme.containers.provider import ContainersProvider
from cfme.containers.service import Service
from cfme.web_ui import toolbar as tb
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.replicator import Replicator
from cfme.containers.pod import Pod


pytestmark = [pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


# CMP-9907 # CMP-9908 # CMP-9909


def test_pods_views():
    """ This test verifies functionality of different views.
        Views that are being tested are: grid view, tile view,
        and list view

    """
    navigate_to(Pod, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Pods grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Pods tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Pods list view setting failed"


# CMP-9918 # CMP-9919 # CMP-9920


def test_replicators_views():
    navigate_to(Replicator, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Replicators grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Replicators tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Replicators list view setting failed"


# CMP-9941 # CMP-9942 # CMP-9943


def test_containers_views():
    navigate_to(Container, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Containers grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Containers tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Containers list view setting failed"


# CMP-9887 # CMP-9888 # CMP-9889


def test_services_views():
    navigate_to(Service, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Services grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Services tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Services list view setting failed"


# CMP-9956 # CMP-9957 # CMP-9958


def test_nodes_views():
    navigate_to(Node, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Nodes grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Nodes tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Nodes list view setting failed"


# CMP-9974 # CMP-9975 # CMP-9976


def test_images_views():
    navigate_to(Image, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Images grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Images tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Images list view setting failed"


# CMP-9984 # CMP-9985 # CMP-9986


def test_imageregistry_views():
    navigate_to(ImageRegistry, 'All')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Images grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Images tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Images list view setting failed"
