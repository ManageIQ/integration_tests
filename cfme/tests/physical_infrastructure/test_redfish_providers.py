# -*- coding: utf-8 -*-
import fauxfactory

from cfme.physical.provider.redfish import RedfishProvider
from cfme.utils.update import update

import pytest

pytestmark = [
    pytest.mark.provider([RedfishProvider], scope="function")
]


def test_redfish_provider_crud(provider, has_no_physical_providers):
    """Tests provider add with good credentials

    Polarion:
        assignee: None
        initialEstimate: None
    """
    provider.create()

    provider.validate_stats(ui=True)

    old_name = provider.name
    with update(provider):
        provider.name = fauxfactory.gen_alphanumeric(8)  # random uuid

    with update(provider):
        provider.name = old_name  # old name

    provider.delete(cancel=False)
    provider.wait_for_delete()
