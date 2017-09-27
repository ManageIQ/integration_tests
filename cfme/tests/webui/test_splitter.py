from xml.sax.saxutils import quoteattr, unescape

import pytest

# from cfme.cloud.instance import Instance
# from cfme.infrastructure.config_management import ConfigManager
# from cfme.infrastructure.datastore import DatastoreCollection
# from cfme.infrastructure.pxe import ISODatastore
# from cfme.infrastructure.virtual_machines import Vm
# from cfme.intelligence.chargeback.rates import ComputeRate
# from cfme.intelligence.reports.reports import CustomReport
import cfme.fixtures.pytest_selenium as sel
from cfme.base.ui import Server
from cfme.exceptions import CannotScrollException
from cfme.infrastructure.networking import InfraNetworking
from cfme.modeling.base import BaseCollection
from cfme.optimize.bottlenecks import Bottlenecks
from cfme.optimize.utilization import Utilization
from cfme.services.myservice import MyService
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
        "model_object,destination", LOCATIONS
    ),
]


@pytest.mark.meta(
    blockers=[
        BZ(1380443, forced_streams=['5.6', '5.7', '5.8'], unblock=lambda location: location[0] !=
            Bottlenecks)
    ]
)
@pytest.mark.requirement('general_ui')
@pytest.mark.tier(3)
def test_pull_splitter_persistence(request, appliance, model_object, destination):
    splitter = Splitter(parent=appliance.browser.widgetastic)

    request.addfinalizer(splitter.reset)

    if model_object == Server:
        model_object = appliance.server
    elif issubclass(model_object, BaseCollection):
        model_object = model_object(appliance)

    navigate_to(model_object, destination)
    # First we move splitter to hidden position by pulling it left twice
    splitter.pull_left()
    splitter.pull_left()
    navigate_to(appliance.server, 'Dashboard')
    try:
        navigate_to(model_object, destination)
    except (TypeError, CannotScrollException):
        # this exception is expected here since
        # some navigation commands try to use accordion when it is hidden by splitter
        pass

    # Then we check hidden position splitter
    if not sel.elements("//div[@id='left_div'][contains(@class, 'hidden-md')]"):
        pytest.fail("Splitter did not persist when on hidden position!")
    # Then we iterate over all the other positions
    for position in ["col-md-2", "col-md-3", "col-md-4", "col-md-5"]:
        # Pull splitter left
        splitter.pull_right()
        navigate_to(appliance.server, 'Dashboard')
        navigate_to(model_object, destination)
        # Then check its position
        if not sel.elements(
                "//div[@id='left_div'][contains(@class, {})]".format(
                    unescape(quoteattr(position)))):
            pytest.fail("Splitter did not persist when on " + str(position) + " position!")
