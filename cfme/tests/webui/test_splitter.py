import pytest
from xml.sax.saxutils import quoteattr, unescape

from cfme.exceptions import CannotScrollException
from cfme.base.ui import Server
from cfme.cloud.instance import Instance
from cfme.infrastructure.config_management import ConfigManager
from cfme.infrastructure.datastore import Datastore
from cfme.infrastructure.pxe import ISODatastore
from cfme.infrastructure.virtual_machines import Vm
from cfme.intelligence.chargeback import ComputeRate
from cfme.intelligence.reports.reports import CustomReport
from cfme.services.myservice import MyService
from cfme.web_ui.splitter import pull_splitter_left, pull_splitter_right
from utils import version
from utils.appliance.implementations.ui import navigate_to
from utils.blockers import BZ


LOCATIONS = [
    "control_explorer", "automate_explorer", "automate_customization", MyService,
    "services_catalogs", "services_workloads", CustomReport, ComputeRate, Instance, Vm,
    ISODatastore, Server, Datastore, ConfigManager, "utilization", "bottlenecks",
    "infrastructure_networking"]


pytestmark = [pytest.mark.parametrize("location", LOCATIONS), pytest.mark.uncollectif(lambda
    location: location == "infrastructure_networking" and version.current_version() < '5.7')]


def nav_to(location):
    if isinstance(location, basestring):
        pytest.sel.force_navigate(location)
    else:
        if location is Vm:
            dest = 'VMsOnly'
        elif location is Server:
            dest = 'Configuration'
        else:
            dest = 'All'

        navigate_to(location, dest)


@pytest.mark.meta(
    blockers=[
        BZ('1380443', unblock=lambda location: location != "bottlenecks")
    ]
)
@pytest.mark.requirement('general_ui')
@pytest.mark.tier(3)
def test_pull_splitter_persistence(location):
    nav_to(location)
    # First we move splitter to hidden position by pulling it left twice
    pull_splitter_left()
    pull_splitter_left()
    navigate_to(Server, 'Dashboard')
    try:
        nav_to(location)
    except (TypeError, CannotScrollException):
        # this exception is expected here since
        # some navigation commands try to use accordion when it is hidden by splitter
        pass

    # Then we check hidden position splitter
    if not pytest.sel.elements("//div[@id='left_div'][contains(@class, 'hidden-md')]"):
        pytest.fail("Splitter did not persist when on hidden position!")
    # Then we iterate over all the other positions
    for position in ["col-md-2", "col-md-3", "col-md-4", "col-md-5"]:
        # Pull splitter left
        pull_splitter_right()
        navigate_to(Server, 'Dashboard')
        nav_to(location)
        # Then check its position
        if not pytest.sel.elements("//div[@id='left_div'][contains(@class, {})]"
                .format(unescape(quoteattr(position)))):
            pytest.fail("Splitter did not persist when on " + str(position) + " position!")
