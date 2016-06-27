import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, ButtonGroup, form_buttons
from cfme.configure import settings #noqa
from utils import testgen
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')


# CMP-9936


def test_containers_providers_default_view():
    """ Containers providers default view test

    This test checks successful change of default views settings for Containers --> Providers menu

    Steps:
        * Goes to Settings --> My Settings --> Default Views menu and change the default view
         settings of Containers --> Containers Providers to Grid/Tile/List view
        * Goes to Compute --> Containers --> Providers and verifies the selected view

    """
    # Change the view to Grid View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Containers Providers')
    bg.choose('Grid View')
    sel.click(form_buttons.save)

    # Go to Container Providers and verify that the View changed to Grid View
    sel.force_navigate('containers_providers')
    assert tb.is_active('Grid View'), 'Providers grid view setting failed'

    # Change the view to Tile View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Containers Providers')
    bg.choose('Tile View')
    sel.click(form_buttons.save)

    # Go to Container Providers and verify that the View changed to Tile View
    sel.force_navigate('containers_providers')
    assert tb.is_active('Tile View'), 'Providers tile view setting failed'

    # Change the view to List View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Containers Providers')
    bg.choose('List View')
    sel.click(form_buttons.save)

    # Go to Container Providers and verify that the View changed to Tile View
    sel.force_navigate('containers_providers')
    assert tb.is_active('List View'), 'Providers list view setting failed'

# CMP-9937


def test_containers_projects_default_view():
    """ Containers projects default view test

    This test checks successful change of default views settings for Containers --> Projects menu

    Steps:
        * Goes to Settings --> My Settings --> Default Views menu and change the default view
        settings of Containers --> Containers Projects to Grid/Tile/List view
        * Goes to Compute --> Containers --> Projects and verifies the selected view

    """
    # Change the view to Grid View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Projects')
    bg.choose('Grid View')
    sel.click(form_buttons.save)

    # Go to Container Projects and verify that the View changed to Grid View
    sel.force_navigate('containers_projects')
    assert tb.is_active('Grid View'), 'Projects grid view setting failed'

    # Change the view to Tile View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Projects')
    bg.choose('Tile View')
    sel.click(form_buttons.save)

    # Go to Container Projects and verify that the View changed to Tile View
    sel.force_navigate('containers_projects')
    assert tb.is_active('Tile View'), 'Projects tile view setting failed'

    # Change the view to List View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Projects')
    bg.choose('List View')
    sel.click(form_buttons.save)

    # Go to Container Projects and verify that the View changed to Tile View
    sel.force_navigate('containers_projects')
    assert tb.is_active('List View'), 'Projects list view setting failed'

# CMP-9938


def test_containers_routes_default_view():
    """Containers providers routes view test

    This test checks successful change of default views settings for Containers --> Routes menu

    Steps:
        * Goes to Settings --> My Settings --> Default Views menu and change the default view
        settings of Containers --> Containers Routes to Grid/Tile/List view
        * Goes to Compute --> Containers --> Routes and verifies the selected view

    """
    # change the default view to the following: Container Routes tiles to Grid View
    sel.force_navigate('my_settings_default_views')
    b = ButtonGroup('Routes')
    b.choose('Grid View')
    sel.click(form_buttons.save)

    # Go to Container Routes and verify that the View changed to Grid View
    sel.force_navigate('containers_routes')
    assert tb.is_active('Grid View'), 'Routes grid view setting failed'

    # Change the view to Tile View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Routes')
    bg.choose('Tile View')
    sel.click(form_buttons.save)

    # Go to Container Routes and verify that the View changed to Tile View
    sel.force_navigate('containers_routes')
    assert tb.is_active('Tile View'), 'Routes tile view setting failed'

    # Change the view to List View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Routes')
    bg.choose('List View')
    sel.click(form_buttons.save)

    # Go to Container Routes and verify that the View changed to Tile View
    sel.force_navigate('containers_routes')
    assert tb.is_active('List View'), 'Routes list view setting failed'

# CMP-10003


def test_containers_nodes_default_view():
    """Containers nodes default view test

    This test checks successful change of default views settings for Containers --> Nodes menu

    Steps:
        * Goes to Settings --> My Settings --> Default Views menu and change the default view
        settings of Containers --> Containers Nodes to Grid/Tile/List view
        * Goes to Compute --> Containers --> Nodes and verifies the selected view

    """
    # Change the view to Grid View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Nodes')
    bg.choose('Grid View')
    sel.click(form_buttons.save)

    # Go to Container Nodes and verify that the View changed to Grid View
    sel.force_navigate('containers_nodes')
    assert tb.is_active('Grid View'), 'Nodes grid view setting failed'

    # Change the view to Tile View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Nodes')
    bg.choose('Tile View')
    sel.click(form_buttons.save)

    # Go to Container Nodes and verify that the View changed to Tile View
    sel.force_navigate('containers_nodes')
    assert tb.is_active('Tile View'), 'Nodes tile view setting failed'

    # Change the view to List View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Nodes')
    bg.choose('List View')
    sel.click(form_buttons.save)

    # Go to Container Nodes and verify that the View changed to Tile View
    sel.force_navigate('containers_nodes')
    assert tb.is_active('List View'), 'Nodes list view setting failed'

# CMP-10002


def test_containers_containers_default_view():
    """Containers containers default view test

    This test checks successful change of default views settings for Containers --> Containers menu

    Steps:
        * Goes to Settings --> My Settings --> Default Views menu and change the default view
        settings of Containers --> Containers Containers to Grid/Tile/List view
        * Goes to Compute --> Containers --> Containers and verifies the selected view

    """
    # Change the view to Grid View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Containers')
    bg.choose('Grid View')
    sel.click(form_buttons.save)

    # Go to Container Containers and verify that the View changed to Grid View
    sel.force_navigate('containers_containers')
    assert tb.is_active('Grid View'), 'Containers grid view setting failed'

    # Change the view to Tile View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Containers')
    bg.choose('Tile View')
    sel.click(form_buttons.save)

    # Go to Container Containers and verify that the View changed to Tile View
    sel.force_navigate('containers_containers')
    assert tb.is_active('Tile View'), 'Containers tile view setting failed'

    # Change the view to List View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Containers')
    bg.choose('List View')
    sel.click(form_buttons.save)

    # Go to Container Containers and verify that the View changed to Tile View
    sel.force_navigate('containers_containers')
    assert tb.is_active('List View'), 'Containers list view setting failed'

# CMP-10000


def test_containers_replicators_default_view():
    """Containers replicators default view test

    This test checks successful change of default views settings for Containers --> Replicators menu

    Steps:
        * Goes to Settings --> My Settings --> Default Views menu and change the default view
        settings of Containers --> Containers Replicators to Grid/Tile/List view
        * Goes to Compute --> Containers --> Replicators and verifies the selected view

    """
    # Change the view to Grid View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Replicators')
    bg.choose('Grid View')
    sel.click(form_buttons.save)

    # Go to Container Pods and verify that the View changed to Grid View
    sel.force_navigate('containers_replicators')
    assert tb.is_active('Grid View'), 'Replicators grid view setting failed'

    # Change the view to Tile View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Replicators')
    bg.choose('Tile View')
    sel.click(form_buttons.save)

    # Go to Container Replicators and verify that the View changed to Tile View
    sel.force_navigate('containers_replicators')
    assert tb.is_active('Tile View'), 'Replicators tile view setting failed'

    # Change the view to List View
    sel.force_navigate('my_settings_default_views')
    bg = ButtonGroup('Replicators')
    bg.choose('List View')
    sel.click(form_buttons.save)

    # Go to Container Replicators and verify that the View changed to Tile View
    sel.force_navigate('containers_replicators')
    assert tb.is_active('List View'), 'Replicators list view setting failed'
