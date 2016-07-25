# -*- coding: utf-8 -*-

""" The test_image_registries_views function verifies that
    image registries can be viewed in grid, tile and list views
    The test_project_list_views_function verifies that list view
    is the default view for container projects
"""
import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from utils import testgen
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider')]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# CMP-9986 # CMP-9985 # CMP-9984


def test_image_registries_views():
    sel.force_navigate('containers_image_registries')
    tb.select('Grid View')
    assert tb.is_active(
        'Grid View'), "Image Registries grid view setting failed"
    tb.select('Tile View')
    assert tb.is_active(
        'Tile View'), "Image Registries tile view setting failed"
    tb.select('List View')
    assert tb.is_active(
        'List View'), "Image Registries list view setting failed"

# CMP-9886


def test_projects_list_views():
    sel.force_navigate('containers_projects')
    assert tb.is_active(
        'List View'), "Projects list view setting failed"
