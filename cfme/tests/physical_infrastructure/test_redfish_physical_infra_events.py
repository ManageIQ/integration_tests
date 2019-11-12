"""This module tests Redfish physical infrastructure events."""
import pytest

from cfme.physical.provider.redfish import RedfishProvider


pytestmark = [
    pytest.mark.provider([RedfishProvider], scope="function"),
]

# Name of the source for the events related to the Redfish provider
SOURCE = 'REDFISH'


def test_get_redfish_events_any(setup_provider_funcscope, register_event):
    """
    Test that the provider accounts for any Redfish-related event.

    The test assumes that events are generated regularly without needing to
    trigger any action.
    """
    register_event(source=SOURCE)
