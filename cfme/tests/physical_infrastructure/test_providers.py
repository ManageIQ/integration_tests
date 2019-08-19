# -*- coding: utf-8 -*-
import uuid

import pytest

from cfme import test_requirements
from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.update import update

pytestmark = [
    pytest.mark.provider([LenovoProvider], scope="function")
]


@pytest.mark.tier(3)
@pytest.mark.sauce
@test_requirements.discovery
def test_physical_infra_provider_crud(provider, has_no_providers):
    """Tests provider add with good credentials

    Metadata:
        test_flag: crud

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    provider.create()

    # Fails on upstream, all provider types - BZ1087476
    provider.validate_stats(ui=True)

    old_name = provider.name
    with update(provider):
        provider.name = str(uuid.uuid4())  # random uuid

    with update(provider):
        provider.name = old_name  # old name

    provider.delete()
    provider.wait_for_delete()
