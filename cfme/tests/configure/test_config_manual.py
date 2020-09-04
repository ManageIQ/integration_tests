"""Manual tests"""
import pytest

from cfme import test_requirements


@pytest.mark.manual
@test_requirements.configuration
@pytest.mark.tier(1)
def test_configure_icons_roles_by_server():
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/15h
        testSteps:
            1. Go to Settings -> Configuration and enable all Server Roles.
            2.Navigate to Settings -> Configuration -> Diagnostics -> CFME Region ->
            Roles by Servers.
            3. Click through all Roles and look for missing icons.
        expectedResults:
            1.
            2.
            3. No icons are missing
    """
    pass


@pytest.mark.manual
@test_requirements.settings
@test_requirements.multi_region
@pytest.mark.tier(3)
def test_add_duplicate_subscription():
    """
    Try adding duplicate record

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/6h
        testSteps:
            1. Set up two appliances where first appliance resides in global region (99) and
            second one resides in remote region (10). Those should use the same security key
            2. Add a provider to second appliance
            3. Set replication subscription type to Remote in second appliance
            4. Set replication subscription type to Global in first appliance
            5. Add subscription to second appliance in first appliance
            6. Try adding second subscription to second appliance in first appliance
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. Second subscription hasn't been added. Warning message has appeared
    """
    pass


@pytest.mark.manual
@test_requirements.settings
@test_requirements.multi_region
@pytest.mark.tier(3)
def test_add_bad_subscription():
    """
    Try adding wrong subscriptions like
      1. remote appliance does have remote replication type set
      2. remote appliance isn't available and etc

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseposneg: negative
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Set up two appliances where first appliance resides in global region (99) and
            second one resides in remote region (10). Those should use the same security key
            2. Add a provider to second appliance
            3. Set replication subscription type to Remote in second appliance
            4. Set replication subscription type to Global in first appliance
            5. Try adding subscription to second appliance in first appliance with wrong values
        expectedResults:
            1.
            2.
            3.
            4.
            5. Subscription hasn't been added. Add subscription task has failed
    """
    pass


@pytest.mark.manual
@test_requirements.settings
@test_requirements.multi_region
@pytest.mark.tier(3)
def test_edit_bad_subscription():
    """
    Try changing subscriptions from good to bad or vise versa

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseposneg: negative
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Set up two appliances where first appliance resides in global region (99) and
            second one resides in remote region (10). Those should use the same security key
            2. Add a provider to second appliance
            3. Set replication subscription type to Remote in second appliance
            4. Set replication subscription type to Global in first appliance
            5. Try changing existing subscription values to wrong ones. f.e wrong password
        expectedResults:
            1.
            2.
            3.
            4.
            5. Subscription shouldn't be changed if connection couldn't be established.
            Subscription update task should fail
    """
    pass


@pytest.mark.manual
@test_requirements.settings
@test_requirements.multi_region
@pytest.mark.tier(3)
def test_cancel_subscription():
    """
    Try canceling adding/changing/removing subscriptions

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Set up two appliances where first appliance resides in global region (99) and
            second one resides in remote region (10). Those should use the same security key
            2. Add a provider to second appliance
            3. Set replication subscription type to Remote in second appliance
            4. Set replication subscription type to Global in first appliance
            5. Try canceling adding/changing/removing subscription
        expectedResults:
            1.
            2.
            3.
            4.
            5. made changes should be canceled
    """
    pass


@pytest.mark.manual
@test_requirements.settings
@test_requirements.multi_region
@pytest.mark.tier(3)
def test_change_subscription_type():
    """
    Try setting/removing global/remote subscription

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Set up two appliances where first appliance resides in global region (99) and
            second one resides in remote region (10). Those should use the same security key
            2. Add a provider to second appliance
            3. Set replication subscription type to Remote in second appliance
            4. Set replication subscription type to Global in first appliance
            5. Add subscription to second appliance
            6. Change subscription type from Global to None
            7. Restore Global subscription type and subscription to remote appliance
            8. Change Remote subscription type to None
            9. Restore Remote subscription type
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7.
            8.
            9. remote appliance data should disappear from global appliance when Global or Remote
            subscription type are changed to None.
            remote appliance data should appear again when Global and Remote subscription types
            are set
    """
    pass


@pytest.mark.manual
@test_requirements.settings
@test_requirements.multi_region
@pytest.mark.tier(3)
def test_subscription_disruption():
    """
    Test restoring subscription after temporary disruptions

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseposneg: negative
        caseimportance: medium
        initialEstimate: 1/4h
        testSteps:
            1. Set up two appliances where first appliance resides in global region (99) and
            second one resides in remote region (10). Those should use the same security key
            2. Add a provider to second appliance
            3. Set replication subscription type to Remote in second appliance
            4. Set replication subscription type to Global in first appliance
            5. Add subscription to second appliance in first appliance
            6. Add some disruption in connection between global and remote appliances
            f.e. add iptables rule to reject packets from one appliance to another one
            7. Try provisioning vm from global appliance
            8. Make some noticeable changes in remote appliance's provider
            9. Remove disruption
            10. Try provisioning vm again
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7. Vm was not provisioned. error/warning should clearly describe the reason
            8.
            9. subscription was restored. Vm was provisioned. Changes made in remote appliance
            appeared in global appliance
    """
    pass
