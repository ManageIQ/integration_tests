import pytest
from cfme.web_ui import toolbar as tb
from utils import testgen
from utils.version import current_version
from cfme.containers.route import Route
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.project import Project
from cfme.containers.provider import ContainersProvider

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


views = ['Grid View', 'Tile View', 'List View']


# CMP-9873 # CMP-9874 # CMP-9875


def test_containers_routes_views():
    """
    Click on top right "grid view", "tile view", "list view" icon.
    Verify routes appear in a proper view
    """
    navigate_to(Route, 'All')
    for view in views:
        tb.select(view)
        assert tb.is_active(view), "{}' setting failed".format(view)


# CMP-9866,# CMP-9865


def test_containers_projects_views():
    """
    Click on top right "grid view", "tile view", "list view" icon.
    Verify routes appear in a proper view
    """
    navigate_to(Project, 'All')
    for view in views:
        tb.select(view)
        assert tb.is_active(view), "{}' setting failed".format(view)


# CMP-9859, # CMP-9858, # CMP-9857


def test_containers_providers_views():
    """
    Click on top right "grid view", "tile view", "list view" icon.
    Verify routes appear in a proper view
    """
    navigate_to(ContainersProvider, 'All')
    for view in views:
        tb.select(view)
        assert tb.is_active(view), "{}' setting failed".format(view)
