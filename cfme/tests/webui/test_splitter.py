import pytest
from xml.sax.saxutils import quoteattr, unescape

from cfme.exceptions import CannotScrollException
from cfme.base.ui import Server
from cfme.cloud.instance import Instance
from cfme.infrastructure.config_management import ConfigManager
from cfme.infrastructure.datastore import DatastoreCollection
from cfme.infrastructure.pxe import ISODatastore
from cfme.infrastructure.virtual_machines import Vm
from cfme.intelligence.chargeback.rates import ComputeRate
from cfme.intelligence.reports.reports import CustomReport
from cfme.services.myservice import MyService
from cfme.optimize.utilization import Utilization
from cfme.optimize.bottlenecks import Bottlenecks
from cfme.infrastructure.networking import InfraNetworking
from cfme.utils import version
from cfme.utils.appliance import current_appliance
from cfme.modeling.base import BaseCollection
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

from widgetastic_manageiq import Splitter

# LOCATIONS = [
#     (Server, 'ControlExplorer'), (Server, 'AutomateExplorer'), (Server, 'AutomateCustomization'),
#     (MyService, 'All'), (Server, 'ServiceCatalogsDefault'), (Server, 'WorkloadsDefault'),
#     (CustomReport, 'All'), (ComputeRate, 'All'), (Instance, 'All'), (Vm, 'VMsOnly'),
#     (ISODatastore, 'All'), (Server, 'Configuration'), (DatastoreCollection, 'All'),
#     (ConfigManager, 'All'), (Utilization, 'All'), (InfraNetworking, 'All'), (Bottlenecks, 'All')
# ]
LOCATIONS = [
    (Server, 'ControlExplorer'), (Server, 'AutomateExplorer'), (Server, 'AutomateCustomization'),
    (MyService, 'All'), (Server, 'ServiceCatalogsDefault'), (Server, 'Configuration'),
    (Utilization, 'All'), (InfraNetworking, 'All')
]


pytestmark = [
    pytest.mark.parametrize(
        "location", LOCATIONS, ids=[
            "{}-{}".format(loc[0].__name__, loc[1]) for loc in LOCATIONS]
    ),
    pytest.mark.uncollectif(lambda location: location[0] == InfraNetworking and
        version.current_version() < '5.7')
]


@pytest.mark.meta(
    blockers=[
        BZ(1380443, forced_streams=['5.6', '5.7', '5.8'], unblock=lambda location: location[0] !=
            Bottlenecks)
    ]
)
@pytest.mark.requirement('general_ui')
@pytest.mark.tier(3)
def test_pull_splitter_persistence(request, location, appliance):
    splitter = Splitter(parent=appliance.browser.widgetastic)

    request.addfinalizer(splitter.reset)

    if location[0] == Server:
        location = (current_appliance.server, location[1])
    elif issubclass(location[0], BaseCollection):
        location = (location[0](appliance), location[1])
    navigate_to(*location)

    # TODO: When all WT is complete, use the view for this

    splitter.pull_left()
    splitter.pull_left()
    navigate_to(Server, 'Dashboard')
    try:
        navigate_to(*location)
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
        splitter.pull_right()
        navigate_to(Server, 'Dashboard')
        navigate_to(*location)
        # Then check its position
        if not pytest.sel.elements("//div[@id='left_div'][contains(@class, {})]"
                .format(unescape(quoteattr(position)))):
            pytest.fail("Splitter did not persist when on " + str(position) + " position!")
