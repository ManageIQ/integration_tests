# -*- coding: utf-8 -*-
import pytest

from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.physical.physical_server import PhysicalServerCollection
from cfme.physical.provider.lenovo import LenovoProvider
from cfme import test_requirements

pytestmark = [pytest.mark.tier(3)]

pytest_generate_tests = testgen.generate([LenovoProvider], scope="module")

@pytest.fixture(scope="module")
def physical_server_collection(appliance):
    return appliance.collections.physical_servers

def test_physical_servers_view_displayed(physical_server_collection):
    """Navigate to the physical servers page and verify that servers are displayed"""
    physical_servers_view = navigate_to(physical_server_collection, 'All')
    assert physical_servers_view.is_displayed
