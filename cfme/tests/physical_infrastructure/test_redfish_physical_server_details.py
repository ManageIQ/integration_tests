# -*- coding: utf-8 -*-
import pytest

from cfme.physical.provider.redfish import RedfishProvider

pytestmark = [pytest.mark.provider([RedfishProvider], scope="function")]


@pytest.fixture(scope="function")
def physical_server(appliance, provider, setup_provider_funcscope):
    # Get and return the first physical server
    yield appliance.collections.redfish_physical_servers.all(provider)[0]


def test_redfish_physical_server_details_stats(physical_server):
    """Navigate to the physical server details page and verify that the stats match

    Polarion:
        assignee: None
        initialEstimate: None
    """
    physical_server.validate_stats(ui=True)
