import pytest
from itertools import product
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')


VIEWS = ['Grid View', 'Tile View', 'List View']


# CMP-9873 # CMP-9874 # CMP-9875


@pytest.mark.parametrize('view', product(VIEWS))
def test_containers_routes_views(view):
    """
    Click on top right "grid view", "tile view", "list view" icon.
    Verify routes appear in a proper view
    """
    sel.force_navigate('containers_routes')
    tb.select(''.join(view))
    assert tb.is_active(''.join(view)), "{}' setting failed".format(''.join(view))


# CMP-9866,# CMP-9865


@pytest.mark.parametrize('view', product(VIEWS))
def test_containers_projects_views(view):
    """
    Click on top right "grid view", "tile view", "list view" icon.
    Verify routes appear in a proper view
    """
    sel.force_navigate('containers_projects')
    tb.select(''.join(view))
    assert tb.is_active(''.join(view)), "{}' setting failed".format(''.join(view))


# CMP-9859, # CMP-9858, # CMP-9857


@pytest.mark.parametrize('view', product(VIEWS))
def test_containers_providers_views(view):
    """
    Click on top right "grid view", "tile view", "list view" icon.
    Verify routes appear in a proper view
    """
    sel.force_navigate('containers_providers')
    tb.select(''.join(view))
    assert tb.is_active(''.join(view)), "{}' setting failed".format(''.join(view))
