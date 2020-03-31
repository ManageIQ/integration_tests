"""This test contains necessary smoke tests for the Control."""
import pytest

from cfme import control
from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    test_requirements.control,
    pytest.mark.smoke,
    pytest.mark.tier(2)
]

destinations = [
    control.explorer.ControlExplorer.__name__,
    control.simulation.ControlSimulation.__name__,
    control.import_export.ControlImportExport.__name__,
    control.log.ControlLog.__name__
]

control_explorer_accordions = [
    "Policy Profiles",
    "Policies",
    "Events",
    "Conditions",
    "Actions",
    "Alert Profiles",
    "Alerts"
]


@pytest.fixture(scope="module")
def control_explorer_view(appliance):
    return navigate_to(appliance.server, "ControlExplorer")


@pytest.mark.parametrize("destination", destinations)
def test_control_navigation(destination, appliance):
    """This test verifies presence of destinations of Control tab.

    Steps:
        * Open each destination of Control tab.

    Polarion:
        assignee: jdupuy
        casecomponent: WebUI
        initialEstimate: 1/60h
    """
    # some of views like Control -> Log incredibly long first time
    view = navigate_to(appliance.server, destination, wait_for_view=60)
    assert view.is_displayed


@pytest.mark.parametrize("destination", control_explorer_accordions)
def test_control_explorer_tree(control_explorer_view, destination, appliance):
    """This test checks the accordion of Control/Explorer.

    Steps:
        * Open each accordion tab and click on top node of the tree.

    Polarion:
        assignee: jdupuy
        casecomponent: WebUI
        initialEstimate: 1/60h
    """
    navigate_to(appliance.server, 'ControlExplorer', wait_for_view=30)
    accordion_name = destination.lower().replace(" ", "_")
    accordion = getattr(control_explorer_view, accordion_name)
    accordion.tree.click_path(f"All {destination}")
