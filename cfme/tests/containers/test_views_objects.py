# -*- coding: utf-8 -*-


""" the test verifies functionality
    of different views such as grid view, tile view
    and list view
"""

import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from utils import testgen
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.5"),
    pytest.mark.usefixtures('setup_provider')]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# CMP-9907 # CMP-9908 # CMP-9909


def test_pods_views():
    sel.force_navigate('containers_pods')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Pods grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Pods tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Pods list view setting failed"


# CMP-9918 # CMP-9919 # CMP-9920


def test_replicators_views():
    sel.force_navigate('containers_replicators')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Replicators grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Replicators tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Replicators list view setting failed"


# CMP-9941 # CMP-9942 # CMP-9943


def test_containers_views():
    sel.force_navigate('containers_containers')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Containers grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Containers tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Containers list view setting failed"


# CMP-9887 # CMP-9888 # CMP-9889


def test_services_views():
    sel.force_navigate('containers_services')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Services grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Services tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Services list view setting failed"


# CMP-9956 # CMP-9957 # CMP-9958


def test_nodes_views():
    sel.force_navigate('containers_nodes')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Nodes grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Nodes tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Nodes list view setting failed"


# CMP-9974 # CMP-9975 # CMP-9976


def test_images_views():
    sel.force_navigate('containers_images')
    tb.select('Grid View')
    assert tb.is_active('Grid View'), "Images grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active('Tile View'), "Images tile view setting failed"
    tb.select('List View')
    assert tb.is_active('List View'), "Images list view setting failed"
