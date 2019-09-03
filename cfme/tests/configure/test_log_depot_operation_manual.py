# -*- coding: utf-8 -*-
# Manual tests for log depot
import pytest

from cfme import test_requirements

pytestmark = [test_requirements.log_depot, pytest.mark.manual]


@pytest.mark.tier(1)
def test_log_collect_current_zone_multiple_servers_server_setup():
    """
    using any type of depot check collect current log function under zone.
    Zone should have multiplie servers under it. Zone should not be setup,
    servers should

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(1)
def test_log_collect_all_zone_zone_multiple_servers_server_setup():
    """
    using any type of depot check collect all log function under zone.
    Zone should have multiplie servers under it. Zone should not be setup,
    servers should

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(1)
def test_log_collect_current_zone_multiple_servers():
    """
    using any type of depot check collect current log function under zone,
    zone has multiplie servers under it. Zone and all servers should have
    theire own settings

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(1)
def test_log_collect_all_zone_multiple_servers():
    """
    using any type of depot check collect all log function under zone.
    Zone should have multiplie servers under it. Zone and all servers
    should have their own settings

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(1)
def test_log_multiple_servers_unconfigured():
    """
    Verify that buttons are unclickable (grayed) when log collection
    unconfigured in all servers under one zone

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        testSteps:
            1.Configure two appliances to work under one zone
              (distribution mode, one master, another slave)
            2. Open appliance"s WebUi -> Settings -> Configuration
            3. Go to Diagnostics tab -> Collect logs
            4. Select second server (slave) and press "collect" select bar
    """
    pass


@pytest.mark.tier(1)
def test_log_collect_all_zone_unconfigured():
    """
    check collect all logs under zone when both levels are unconfigured.
    Expected result - all buttons are disabled

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(1)
def test_log_collect_current_zone_all_unconfigured():
    """
    check collect logs under zone when both levels are unconfigured.
    Expected result - all buttons are disabled

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_log_collection_via_ftp_over_ipv6():
    """
    Bug 1452224 - Log Collection fails via IPv6

    Bugzilla:
        1452224

    An IPv6 FTP server can be validated for log collection, and log
    collection succeeds.

    # subscription-manager register
    # subscription-manager attach --pool 8a85f98159d214030159d24651155286
    # yum install vsftpd
    # vim /etc/vsftpd/vsftpd.conf
    anon_upload_enable=YES
    anon_mkdir_write_enable=YES
    # ip6tables -F
    # setenforce 0
    # systemctl start vsftpd
    # mkdir /var/ftp/pub/anon
    # chmod 777 /var/ftp/pub/anon
    Administrator > Configuration > Diagnostics > Collect Logs > Edit
    Type        Anonymous FTP
    Depot Name    tpapaioa
    URI        ftp://localhost6/pub/anon
    > Save
    Collect > Collect current logs
    Refresh after a couple minutes
    Basic Info
    Log Depot URI        ftp://localhost6/pub/anon
    Last Log Collection    2018-01-10 20:29:31 UTC
    Last Message        Log files were successfully collected

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        title: Log collection via FTP over IPv6
    """
    pass
