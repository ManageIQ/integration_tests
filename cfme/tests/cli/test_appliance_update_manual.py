# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_upgrade_rubyrep_to_pglogical():
    """
    Test upgrading appliances in ruby replication and change it over to
    pglogical

    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: medium
        endsin: 5.9
        initialEstimate: 1h
        setup: provision 2 appliances
               setup rubyrep between them
               test replication is working
               stop replication
               upgrade appliances following version dependent docs found here
               https://mojo.redhat.com/docs/DOC-1058772
               configure pglogical replication
               confirm replication is working correctly
        startsin: 5.6
        testtype: upgrade
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_update_webui_ipv6():
    """
    Test updating the appliance to release version from prior version.
    (i.e 5.5.x to 5.5.x+) IPV6 only env

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: -Provision configured appliance
               -Register it with RHSM using web UI
               -Create /etc/yum.repos.d/update.repo
               -populate file with repos from
               https://mojo.redhat.com/docs/DOC-1058772
               -check for update in web UI
               -apply update
               -appliance should shutdown update and start back up
               -confirm you can login afterwards
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_upgrade_single_inplace_ipv6():
    """
    Upgrading a single appliance on ipv6 only env

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: provision appliance
               add provider
               add repo file to /etc/yum.repos.d/
               run "yum update"
               run "rake db:migrate"
               run "rake evm:automate:reset"
               run "systemctl start evmserverd"
               check webui is available
               add additional provider/provision vms
        startsin: 5.9
    """
    pass
