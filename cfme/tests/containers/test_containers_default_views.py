import pytest
from itertools import product
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, ButtonGroup, form_buttons
from cfme.configure import settings  # noqa
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(3)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')


VIEWS = ['Grid View', 'Tile View', 'List View']
BUTTON_GROUP = ['Containers Providers', 'Projects', 'Routes', 'Nodes', 'Containers', 'Replicators']

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
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup(button_group)
    bg.choose(view)
    sel.click(form_buttons.save)
    if button_group == 'Containers Providers':
        location = 'containers_providers'
    elif button_group == 'Projects':
        location = 'containers_projects'
    elif button_group == 'Routes':
        location = 'containers_routes'
    elif button_group == 'Nodes':
        location = 'containers_nodes'
    elif button_group == 'Containers':
        location = 'containers_containers'
    elif button_group == 'Replicators':
        location = 'containers_replicators'
    sel.force_navigate(location)
    assert tb.is_active(view), "{}'s {} setting failed".format(view, button_group)
