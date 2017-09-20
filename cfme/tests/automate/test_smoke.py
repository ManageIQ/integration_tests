# -*- coding: utf-8 -*-
"""This test contains necessary smoke tests for the Automate."""
import pytest

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection

pytestmark = [
    test_requirements.automate,
    pytest.mark.smoke,
    pytest.mark.tier(2),
    pytest.mark.ignore_stream(("upstream", {"domain_name": "RedHat"}))
]


@pytest.mark.parametrize("domain_name", ["ManageIQ", "RedHat"])
def test_domain_present(domain_name, soft_assert, appliance):
    """This test verifies presence of domains that are included in the appliance.

    Prerequisities:
        * Clean appliance.

    Steps:
        * Open the Automate Explorer.
        * Verify that all of the required domains are present.
    """
    dc = DomainCollection(appliance)
    domain = dc.instantiate(name=domain_name)
    soft_assert(domain.exists, "Domain {} does not exist!".format(domain_name))
    soft_assert(domain.locked, "Domain {} is not locked!".format(domain_name))
    soft_assert(
        appliance.check_domain_enabled(
            domain_name), "Domain {} is not enabled!".format(domain_name))
