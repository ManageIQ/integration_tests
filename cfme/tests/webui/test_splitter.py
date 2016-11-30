import pytest
from cfme.web_ui.splitter import pull_splitter_left, pull_splitter_right
from xml.sax.saxutils import quoteattr, unescape
from utils import version
from utils.blockers import BZ
LOCATIONS = [
    "control_explorer", "automate_explorer", "automate_customization", "my_services",
    "services_catalogs", "services_workloads", "reports", "chargeback", "clouds_instances_no_tree",
    "infrastructure_virtual_machines_no_tree", "infrastructure_pxe", "configuration",
    "infrastructure_datastores_no_tree", "infrastructure_config_management", "utilization",
    "bottlenecks",
    "infrastructure_networking"]

pytestmark = [pytest.mark.parametrize("location", LOCATIONS), pytest.mark.uncollectif(lambda
    location: location == "infrastructure_networking" and version.current_version() < '5.7')]


@pytest.mark.meta(
    blockers=[
        BZ('1380443', unblock=lambda location: location != "bottlenecks")
    ]
)
@pytest.mark.requirement('general_ui')
@pytest.mark.tier(3)
def test_pull_splitter_persistence(location):
    pytest.sel.force_navigate(location)
    # First we move splitter to hidden position by pulling it left twice
    pull_splitter_left()
    pull_splitter_left()
    pytest.sel.force_navigate("dashboard")
    pytest.sel.force_navigate(location)
    # Then we check hidden position splitter
    if not pytest.sel.elements("//div[@id='left_div'][contains(@class, 'hidden-md')]"):
        pytest.fail("Splitter did not persist when on hidden position!")
    # Then we iterate over all the other positions
    for position in ["col-md-2", "col-md-3", "col-md-4", "col-md-5"]:
        # Pull splitter left
        pull_splitter_right()
        pytest.sel.force_navigate("dashboard")
        pytest.sel.force_navigate(location)
        # Then check its position
        if not pytest.sel.elements("//div[@id='left_div'][contains(@class, {})]"
                .format(unescape(quoteattr(position)))):
            pytest.fail("Splitter did not persist when on " + str(position) + " position!")
