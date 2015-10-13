# -*- coding: utf-8 -*-
import pytest

from cfme.web_ui.mixins import pull_splitter, left_half_size
from utils.version import current_version


TOLERANCE = 20
LOCATIONS = [
    "control_explorer", "automate_explorer", "automate_customization", "my_services",
    "services_catalogs", "services_workloads", "reports", "chargeback", "clouds_instances",
    "infrastructure_virtual_machines", "infrastructure_pxe", "configuration"]


@pytest.mark.parametrize("location", LOCATIONS)
@pytest.mark.meta(blockers=[1219019])
@pytest.mark.uncollectif(lambda: current_version() >= "5.5")
def test_pull_splitter(location):
    """This test tests whether the setting of the position of the left/right splitter is persisted
    correctly."""
    pytest.sel.force_navigate(location)
    pull_splitter(-100)
    original_position = left_half_size()
    pytest.sel.force_navigate("dashboard")
    pytest.sel.force_navigate(location)
    assert (
        original_position - TOLERANCE <= left_half_size() <= original_position + TOLERANCE,
        "Splitter fail!")
