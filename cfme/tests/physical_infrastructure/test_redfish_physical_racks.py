import pytest

from cfme.physical.provider.redfish import RedfishProvider

pytestmark = [pytest.mark.provider([RedfishProvider], scope="function")]


def get_physical_racks(appliance, provider):
    """Get and return the physical racks collection."""
    return appliance.collections.redfish_physical_racks.all(provider)


def test_redfish_physical_racks_details_stats(appliance, provider, setup_provider_funcscope):
    """Navigate to the physical racks' details page and verify that the stats match."""
    for physical_rack in get_physical_racks(appliance, provider):
        physical_rack.validate_stats(ui=True)
