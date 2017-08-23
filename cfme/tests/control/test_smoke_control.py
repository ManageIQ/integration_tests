# -*- coding: utf-8 -*-
"""This test contains necessary smoke tests for the Control."""
import pytest

from cfme.base import Server
from cfme import control, test_requirements
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
def control_explorer_view():
    return navigate_to(Server, "ControlExplorer")


@pytest.mark.parametrize("destination", destinations)
def test_control_navigation(destination):
    """This test verifies presence of destinations of Control tab.

    Steps:
        * Open each destination of Control tab.
    """
    view = navigate_to(Server, destination)
    assert view.is_displayed


@pytest.mark.parametrize("destination", control_explorer_accordions)
def test_control_explorer_tree(control_explorer_view, destination):
    """This test checks the accordion of Control/Explorer.

    Steps:
        * Open each accordion tab and click on top node of the tree.
    """
    accordion_name = destination.lower().replace(" ", "_")
    accordion = getattr(control_explorer_view, accordion_name)
    accordion.tree.click_path("All {}".format(destination))
