# -*- coding: utf-8 -*-
# pylint: skip-file
"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.ignore_stream('upstream')]


@pytest.mark.manual
@test_requirements.satellite
def test_no_rbac_warnings_in_logs_when_viewing_satellite_provider():
    """
    RBAC-related warnings logged when viewing Satellite provider in web UI

    Bugzilla:
        1565266
    1.) Add Satellite provider.
    2.) Click on items under Providers accordion.
    3.) View evm.log. No WARN-level messages should be logged.
    [----] W, [2018-04-09T14:09:19.654859 #13384:84e658]  WARN -- :
    MIQ(Rbac::Filterer#lookup_method_for_descendant_class) could not find
    method name for ConfiguredSystem::ConfiguredSystem

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/15h
    """
    pass


@pytest.mark.manual
@test_requirements.satellite
def test_satellite_host_groups_show_up_as_configuration_profiles_satellite_62():
    """
    For the Satellite provider satellite_62, both the centos and fedora-
    cloud configuration profiles show up in Configuration > Manage, in the
    accordion menu under All Configuration Manager Providers > Red Hat
    Satellite Providers > satellite_62 Configuration Manager.

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/15h
    """
    pass


@pytest.mark.manual
@test_requirements.satellite
def test_satellite_credential_validation_times_out_with_error_message():
    """
    Bug 1564601 - Satellite credential validation times out with no error
    message

    Bugzilla:
        1564601

    When adding a new Satellite configuration provider, if the URL cannot
    be accessed because of a firewall dropping packets, then credential
    validation should time out after 2 minutes with a flash message.

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass
