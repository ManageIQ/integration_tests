import pytest
from itertools import product
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, ButtonGroup, form_buttons
from cfme.base import Server
from cfme.containers.container import Container
from cfme.containers.provider import ContainersProvider
from cfme.containers.project import Project
from cfme.containers.route import Route
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
import cfme.web_ui.tabstrip as tabs
from cfme.configure import settings  # noqa
from utils import testgen
from utils.version import current_version
from utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')


VIEWS = ['Grid View', 'Tile View', 'List View']
BUTTON_GROUP = ['Containers Providers', 'Projects', 'Routes', 'Nodes', 'Containers', 'Replicators']

# TODO: Replace with navigator registered destinations when all container objects support them
mapping = {
    'Containers Providers': 'containers_providers',
    'Projects': 'containers_projects',
    'Routes': 'containers_routes',
    'Nodes': 'containers_nodes',
    'Containers': 'containers_containers',
    'Replicators': 'containers_replicators',
}

# CMP-9936 # CMP-9937 # CMP-9938 # CMP-10000 # CMP-10001 # CMP-10003


@pytest.mark.parametrize(('button_group', 'view'), product(BUTTON_GROUP, VIEWS))
def test_containers_providers_default_view(button_group, view):
    """ Containers Providers/Projects/Routes/Nodes/Containers/Replicators default view test
        This test checks successful change of default views settings for Containers -->
        Providers/Projects/Routes/Nodes/Containers/Replicators menu
        Steps:
            * Goes to Settings --> My Settings --> Default Views menu and change the default view
             settings of Containers --> Containers Providers/Projects/Routes/Nodes
             /Containers/Replicators
              to Grid/Tile/List view
            * Goes to Compute --> Containers --> Providers and verifies the selected view
        """
    navigate_to(Server, 'MySettings')
    tabs.select_tab("Default Views")
    bg = ButtonGroup(button_group)
    bg.choose(view)
    sel.click(form_buttons.save)
    if button_group == 'Containers Providers':
        navigate_to(ContainersProvider, 'All')
    elif button_group == 'Projects':
        navigate_to(Project, 'All')
    elif button_group == 'Routes':
        navigate_to(Route, 'All')
    elif button_group == 'Nodes':
        navigate_to(Node, 'All')
    elif button_group == 'Containers':
        navigate_to(Container, 'All')
    elif button_group == 'Replicators':
        navigate_to(Replicator, 'All')
    assert tb.is_active(view), "{}'s {} setting failed".format(view, button_group)
