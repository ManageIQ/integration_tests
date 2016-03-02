# -*- coding: utf-8 -*-
"""This test contains necessary smoke tests for the Automate."""
import pytest

from cfme.automate.explorer import Domain
from utils import db_queries as dbq

pytestmark = [
    pytest.mark.smoke,
    pytest.mark.ignore_stream(("upstream", {"domain_name": "RedHat"}))
]


@pytest.mark.parametrize("domain_name", ["ManageIQ", "RedHat"])
def test_domain_present(domain_name, soft_assert):
    """This test verifies presence of domains that are included in the appliance.

    Prerequisities:
        * Clean appliance.

    Steps:
        * Open the Automate Explorer.
        * Verify that all of the required domains are present.
    """
    domain = Domain(domain_name)
    soft_assert(domain.exists, "Domain {} does not exist!".format(domain_name))
    soft_assert(domain.is_locked, "Domain {} is not locked!".format(domain_name))
    soft_assert(
        dbq.check_domain_enabled(domain_name), "Domain {} is not enabled!".format(domain_name))
