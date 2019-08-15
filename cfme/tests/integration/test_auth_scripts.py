# -*- coding: utf-8 -*-
import pytest


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1577303])
def test_fixauth_dryrun_has_feedback(temp_appliance_preconfig):
    """
    Check whether the fixauth says it is running in dry mode

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        initialEstimate: 1/60h

    Bugzilla:
        1577303
    """
    appliance = temp_appliance_preconfig
    run_command = appliance.ssh_client.run_command
    dry_run_message = (
        'is executing in dry-run mode, and no actual changes will be made **')
    assert dry_run_message in run_command("fix_auth -d").output
    assert dry_run_message in run_command("fix_auth -d -i invalid").output
    assert dry_run_message in run_command("fix_auth -d --databaseyml").output
    assert dry_run_message not in run_command("fix_auth").output
