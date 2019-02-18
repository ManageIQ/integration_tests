"""Manual tests"""
import pytest

from cfme import test_requirements


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
@pytest.mark.ignore_stream('5.9')
def test_custom_service_dialog_quota_flavors():
    """
    Test quota with instance_type in custom dialog

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        caseimportance: low
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: Configuration
        tags: quota
        title: Test quota with instance_type in custom dialog
        testSteps:
            1. Set tenant quota for storage.
            2. Create a service dialog with field: option_0_instance_type
            3. Attach that dialog to catalog item
            4. Order the service by changing the flavor from the drop-down list.

        expectedResults:
            1.
            2.
            3. Quota exceeded message should be displayed

    Bugzilla:
        1499193, 1581288, 1657628
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(3)
def test_quota_for_simultaneous_service_catalog_request_with_different_users():
    """
    This test case is to test quota for simultaneous service catalog request with different users.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        caseimportance: low
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: Provisioning
        tags: quota
        title: Test quota for simultaneous service catalog request with different users
        testSteps:
            1. Create a service catalog with vm_name, instance_type &
               number_of_vms as fields.
            2. Set quotas threshold values for number_of_vms to 5
            3. Create two users from same group try to provision service catalog from different
               web-sessions with more that quota limit
        expectedResults:
            1.
            2.
            3. Quota exceeded message should be displayed

    Bugzilla:
        1456819

    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(2)
@pytest.mark.ignore_stream('5.9', '5.10')
def test_instance_quota_reconfigure_with_flavors():
    """
    Test reconfiguration of instance using flavors after setting quota but this is RFE which is not
    yet implemented.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/6h
        caseimportance: low
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: Cloud
        tags: quota
        title: test quota for ansible service
        testSteps:
            1. Add openstack provider
            2. Set quota
            3. Provision instance under the quota limit
            4. Reconfigure this instance and provision it with changing flavors
        expectedResults:
            1.
            2.
            3. Provision instance successfully
            4. Provision instance request should be denied

    Bugzilla:
        1473325
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_quota_for_ansible_service():
    """
    This test case is to test quota for ansible service

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        caseimportance: low
        caseposneg: positive
        testtype: functional
        startsin: 5.5
        casecomponent: Configuration
        tags: quota
        title: test quota for ansible service
        testSteps:
            1. create a service bundle including an Ansible Tower service type
            2. make sure CloudForms quotas are enabled
            3. provision the service
        expectedResults:
            1.
            2.
            3. No error in service bundle provisioning for Ansible Tower service types when quota
               is enforce.

    Bugzilla:
        1363901
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_quota_calculation_using_service_dialog_overrides():
    """
    This test case is to check Quota calculation using service dialog overrides.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/6h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: Infra
        tags: quota
        title: Test Quota calculation using service dialog overrides.
        testSteps:
            1. create a new domain quota_test
            2. Using the Automate Explorer, copy the
               ManageIQ/System/CommonMethods/QuotaMethods/requested method
               to the quota_test domain.
            3. Import the attached dialog. create catalog and catalog
               item using this dialog
            4. create a child tenant and set quota. create new group and
               user for this tenant.
            5. login with this user and provision by overriding values
            6. Also test the same for user and group quota source type
        expectedResults:
            1.
            2.
            3.
            4.
            5. Quota should be denied with reason for quota exceeded message
            6. Quota should be denied with reason for quota exceeded message

    Bugzilla:
        1492158
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(3)
def test_service_template_provisioning_quota_for_number_of_vms_using_custom_dialog():
    """
    This test case is to test service template provisioning quota for number of vm's using custom
    dialog.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: Provisioning
        tags: quota
        title: test service template provisioning quota for number of vm's using custom dialog
        testSteps:
            1. Create a service catalog with vm_name, instance_type &
               number_of_vms as fields.
            2. Set quotas threshold values for number_of_vms to 5
            3. Provision service catalog with vm count as 10.
        expectedResults:
            1.
            2.
            3. CFME should show quota exceeded message for VMs requested

    Bugzilla:
        1455844
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(3)
def test_quota_enforcement_for_cloud_volumes():
    """
    This test case is to test quota enforcement for cloud volumes

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: Provisioning
        tags: quota
        title: test quota enforcement for cloud volumes
        testSteps:
            1. Add openstack provider
            2. Set quota for storage
            3. While provisioning instance; add cloud volume with values
            4. Submit the request and see the last message in request info row
        expectedResults:
            1.
            2.
            3.
            4. Last message should show requested storage value is equal to
               instance type's default storage + volume storage value added while provisioning.

    Bugzilla:
        1455349
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(2)
def test_quota_with_invalid_service_request():
    """
    This test case is to test quotas with various regions and invalid service requests
    To reproduce this issue: (You"ll need to have the RedHat Automate
    domain)

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Control
        tags: quota
        title: Test multiple tenant quotas simultaneously
        testSteps:
            1. Setup multiple zones.(You can use a single appliance and just add a "test" zone)
            2. Add VMWare provider and configure it to the "test" zone.
            3. Create a VMWare Service Item.
            4. Order the Service.
            5. Delete the Service Template used in the Service creation in step 3.
            6. Modify the VMWare provider to use the default zone. (This should
               leave the existing Service request(s) in the queue for the "test" zone
               and the service_template will be invalid)
            7. Provision a VMWare VM.
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. You should see the following error in the log:
               "[----] E, [2018-01-06T11:11:20.073924 #13027:e0ffc4] ERROR -- :
               Q-task_id([miq_provision_787]) MiqAeServiceModelBase.ar_method raised:
               <NoMethodError>: <undefined method `service_resources" for
               nil:NilClass> [----] E, [2018-01-06T11:11:20.074019 #13027:e0ffc4] ERROR -- :
               Q-task_id([miq_provision_787])"

    Bugzilla:
        1534589, 1531914
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(2)
def test_simultaneous_tenant_quota():
    """
    Test multiple tenant quotas simultaneously

    Polarion:
        assignee: ghubale
        initialEstimate: 1/6h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: Provisioning
        tags: quota
        title: Test multiple tenant quotas simultaneously
        testSteps:
            1. Create tenant1 and tenant2.
            2. Create a project under tenant1 or tenant2
            3. Enable quota for cpu, memory or storage etc
            4. Create a group and add role super_administrator
            5. Create a user and add it to the group
            6. Login with the newly created user in the service portal. Take multiple items which go
               over the allocated quota
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. CFME should cancel or notify that multiple items which are above assigned quota
               are cancelled

    Bugzilla:
        1456819, 1401251

    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(2)
def test_notification_show_notification_when_quota_is_exceed():
    """
    This test case is to check when quota is exceeded, CFME should notify with reason.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: Services
        tags: quota
        title: Notification - Show notification when quota is exceeded
        testSteps:
            1. Add provider
            2. Set quota
            3. Provision VM via service or life cylce with more than quota assigned
        expectedResults:
            1.
            2.
            3. CFME should notify with reason why provision VM is denied
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_quota_not_fails_after_vm_reconfigure_disk_remove():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: Infra
        tags: quota
        testSteps:
            1. Add infra provider and Add disk(s) to a vm instance
            2. Turn quota on
            3. Try to remove the disk(s)
        expectedResults:
            1.
            2.
            3. Request should be successful and size of disk(s) should be included in quota
               requested.

     Bugzilla:
        1644351
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_quota_exceed_mail_with_more_info_link():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/12h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Infra
        tags: quota
        testSteps:
            1. Setup smtp for cfme using https://mojo.redhat.com/videos/925032
            2. See if you are Able to see the expected link address in an email for Quota Exceeded.

    Bugzilla:
        1579031
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_custome_role_modify_for_dynamic_product_feature():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/12h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: Configuration
        tags: quota
        testSteps:
            1. create two tenants
            2. create new custom role using existing role
            3. Update newly created custom role by doing uncheck in to options provided under
               automation > automate > customization > Dialogs > modify > edit/add/copy/delete
               > uncheck for any tenant
            4. You will see save button is not enabled but if you changed 'Name' or
               'Access Restriction for Services, VMs, and Templates' then save button is getting
               enabled.
            5. It updates changes only when we checked or unchecked for all of the tenants under
               edit/add/copy/delete options.

    Bugzilla:
        1655012
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_dynamic_product_feature_for_tenant_quota():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/12h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: Configuration
        tags: quota
        testSteps:
            1. Add two users > alpha and omega
            2. Create two tenants > alpha_tenant and it's child - omega_tenant
            3. Create two custom roles (role_alpha and role_omega) from copying
               EvmRole-tenant_administrator role
            4. Create groups alpha_group(for alpha_tenant) and omega_group(for omega_tenant)
               then assign role_alpha
               to alpha_group and role_omega to omega_group
            5. Add alpha_group to alpha user and omega_group to omega user
            6. Modify role_alpha for manage quota permissions of alpha user as it will manage
               only quota of omega_tenant
            7. Modify role_omega for manage quota permissions of omega user as it will not even
               manage quota of itself or other tenants
            8. CHECK IF YOU ARE ABLE TO MODIFY THE "MANAGE QUOTA" CHECKS IN ROLE AS YOU WANT
            9  Then see if you are able to save these two new roles.
            10. Then login with both users one by one and see if these roles permissions are
                applied or not.
            10a. login with alpha and SEE IF ALPHA USER CAN ABLE TO SET QUOTA OF omega_tenant
                 FOR CPU - 5
            11b. login with omega and SEE QUOTA GETS CHANGED OR NOT. THEN TRY TO CHANGE QUOTA
                 IMPOSED BY ALPHA USER.
            12c. Here as per role_omega permissions, omega must not able change its own quota or
                 other tenants quota.

    Bugzilla:
        1655012, 1468795
    """
    pass
