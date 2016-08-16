# -*- coding: utf-8 -*-

""" Polarion test cases CMP-9986, 9985, 9984, 9886
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


def test_projects_list_views():
    sel.force_navigate('containers_projects')
    assert tb.is_active(
        'List View'), "Projects list view setting failed"
