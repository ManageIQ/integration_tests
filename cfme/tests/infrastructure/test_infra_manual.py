# -*- coding: utf-8 -*-
# pylint: skip-file
"""Manual tests"""

import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.ignore_stream("5.9", "5.10", "upstream")]


@pytest.mark.manual
@test_requirements.discovery
@pytest.mark.tier(1)
def test_domain_id_required_validation():
    """
    Steps:1. Try to add OpenStack provider
    2. Select Keystone V3 as for it only we need to set domain id
    3. don"t fill domain id
    4. Verify
    5. check for flash
    https://bugzilla.redhat.com/show_bug.cgi?id=1545520

    Polarion:
        assignee: pvala
        casecomponent: infra
        caseimportance: low
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.discovery
@pytest.mark.tier(1)
def test_infrastructure_providers_rhevm_edit_provider_no_default_port():
    """
    1) Add a rhevm provider
    2) Edit it and try to change it to another rhevm provider
    3) There shouldn"t be any default API port and API port should be
    blank

    Polarion:
        assignee: pvala
        casecomponent: infra
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.discovery
def test_add_infra_provider_screen():
    """
    Manually add provider using Add screen
    Provider Add:
    -test form validation using incorrect format for each field
    -test wrong ip
    -test wrong credentials
    -test verify cretentials
    -test verify wrong credentials
    -test wrong security protocol
    -test wrong provider type

    Polarion:
        assignee: pvala
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass
