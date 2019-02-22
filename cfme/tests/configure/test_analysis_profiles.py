# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.blockers import BZ
from cfme.utils.update import update

pytestmark = [pytest.mark.tier(3)]

# TODO parametrize this with some data fuzzing
files_list = [{'Name': '/etc/test/true', 'Collect Contents?': True},
              {'Name': '/etc/test/false', 'Collect Contents?': False}]
categories_list = ['System', 'User Accounts']
registry_list = [{'Registry Key': 'test-reg-key',
                  'Registry Value': 'test-reg-value'}]
events_list = [{'Name': 'test-event',
                'Filter Message': 'test-msg',
                'Source': 'test-src',
                '# of Days': '5'}]

updated_files = [
    {'Name': files_list[0]['Name'],
     'Collect Contents?': not files_list[0]['Collect Contents?']}]

TENANT_NAME = "tenant_{}".format(fauxfactory.gen_alphanumeric())


def events_check(updates=False):
    form_bug = BZ(1485953, forced_streams=['upstream'])
    if updates:
        return updated_files if not form_bug.blocks else None
    else:
        return events_list if not form_bug.blocks else None


@pytest.fixture
def default_host_profile(analysis_profile_collection):
    return analysis_profile_collection.instantiate(
        name="host sample",
        description='Host Sample',
        profile_type=analysis_profile_collection.HOST_TYPE
    )


@pytest.fixture
def analysis_profile_collection(appliance):
    return appliance.collections.analysis_profiles


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_vm_analysis_profile_crud(appliance, soft_assert, analysis_profile_collection):
    """CRUD for VM analysis profiles.

    Polarion:
        assignee: anikifor
        caseimportance: medium
        initialEstimate: 1/2h
        testtype: integration
    """
    vm_profile = analysis_profile_collection.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        profile_type=analysis_profile_collection.VM_TYPE,
        files=files_list,
        categories=categories_list,
        registry=registry_list,
        events=events_check()
    )
    view = appliance.browser.create_view(
        navigator.get_class(analysis_profile_collection, 'All').VIEW)
    vm_flash = vm_profile.name if appliance.version < '5.10' else vm_profile.description
    view.flash.assert_message('Analysis Profile "{}" was saved'.format(vm_flash))

    assert vm_profile.exists

    files_updates = events_check(updates=True)
    with update(vm_profile):
        vm_profile.files = files_updates
    view = appliance.browser.create_view(navigator.get_class(vm_profile, 'Details').VIEW)
    view.flash.assert_success_message('Analysis Profile "{}" was saved'.format(vm_flash))
    soft_assert(vm_profile.files == files_updates,
                'Files update failed on profile: {}, {}'.format(vm_profile.name, vm_profile.files))

    with update(vm_profile):
        vm_profile.categories = ['System']
    soft_assert(vm_profile.categories == ['System'],
                'Categories update failed on profile: {}'.format(vm_profile.name))
    copied_profile = vm_profile.copy(new_name='copied-{}'.format(vm_profile.name))
    view = appliance.browser.create_view(
        navigator.get_class(analysis_profile_collection, 'All').VIEW)
    # yep, not copy specific
    vm_copied_flash = (
        copied_profile.name if appliance.version < '5.10' else copied_profile.description
    )
    view.flash.assert_message('Analysis Profile "{}" was saved'.format(vm_copied_flash))
    assert copied_profile.exists

    copied_profile.delete()
    assert not copied_profile.exists

    vm_profile.delete()
    view.flash.assert_success_message('Analysis Profile "{}": Delete successful'.format(vm_flash))
    assert not vm_profile.exists


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_host_analysis_profile_crud(appliance, soft_assert, analysis_profile_collection):
    """CRUD for Host analysis profiles.

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/12h
    """
    host_profile = analysis_profile_collection.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        profile_type=analysis_profile_collection.HOST_TYPE,
        files=files_list,
        events=events_check()
    )
    view = appliance.browser.create_view(
        navigator.get_class(analysis_profile_collection, 'All').VIEW)
    host_flash = host_profile.name if appliance.version < '5.10' else host_profile.description
    view.flash.assert_message('Analysis Profile "{}" was saved'.format(host_flash))
    assert host_profile.exists

    files_updates = events_check(updates=True)
    with update(host_profile):
        host_profile.files = files_updates
    soft_assert(host_profile.files == files_updates,
                'Files update failed on profile: {}, {}'
                .format(host_profile.name, host_profile.files))
    copied_profile = host_profile.copy(new_name='copied-{}'.format(host_profile.name))
    view = appliance.browser.create_view(
        navigator.get_class(analysis_profile_collection, 'All').VIEW)
    host_copied_flash = (
        copied_profile.name if appliance.version < '5.10' else copied_profile.description
    )
    view.flash.assert_message('Analysis Profile "{}" was saved'.format(host_copied_flash))
    assert copied_profile.exists

    copied_profile.delete()
    assert not copied_profile.exists

    host_profile.delete()
    view.flash.assert_success_message('Analysis Profile "{}": Delete successful'.format(host_flash))
    assert not host_profile.exists


# TODO Combine and parametrize VM + Host validation tests
# Parametrize VM/Host, and (name/description/no item + flash) message as namedtuple
def test_vmanalysis_profile_description_validation(analysis_profile_collection):
    """ Test to validate description in vm profiles

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/20h
    """
    with pytest.raises(AssertionError):
        analysis_profile_collection.create(
            name=fauxfactory.gen_alphanumeric(),
            description=None,
            profile_type=analysis_profile_collection.VM_TYPE,
            categories=categories_list
        )

    # Should still be on the form page after create method raises exception
    view = analysis_profile_collection.create_view(
        navigator.get_class(analysis_profile_collection, 'AddVmProfile').VIEW, wait='10s'
    )
    view.flash.assert_message("Description can't be blank")
    view.cancel.click()


def test_analysis_profile_duplicate_name(analysis_profile_collection):
    """ Test to validate duplicate profiles name.

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/15h
    """
    profile = analysis_profile_collection.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        profile_type=analysis_profile_collection.VM_TYPE,
        categories=categories_list
    )

    with pytest.raises(AssertionError):
        analysis_profile_collection.create(
            name=profile.name,
            description=profile.description,
            profile_type=analysis_profile_collection.VM_TYPE,
            categories=profile.categories
        )

    # Should still be on the form page after create method raises exception
    view = analysis_profile_collection.create_view(
        navigator.get_class(analysis_profile_collection, 'AddVmProfile').VIEW, wait='10s'
    )
    view.flash.assert_message("Name has already been taken")
    view.cancel.click()


def test_delete_default_analysis_profile(default_host_profile, appliance):
    """ Test to validate delete default profiles.

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/15h
    """
    # Option disabled from details
    view = navigate_to(default_host_profile, 'Details')
    assert not view.toolbar.configuration.item_enabled('Delete this Analysis Profile')

    # Flash error from collection
    view = navigate_to(default_host_profile.parent, 'All')
    row = view.entities.table.row(
        name=default_host_profile.name, description=default_host_profile.description
    )
    row[0].check()
    view.toolbar.configuration.item_select('Delete the selected Analysis Profiles',
                                           handle_alert=True)
    view.flash.assert_message('Default Analysis Profile "{}" can not be deleted'.
                              format(default_host_profile.name))


def test_edit_default_analysis_profile(default_host_profile, appliance):
    """ Test to validate edit default profiles.

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/10h
    """
    # Option disabled from details
    view = navigate_to(default_host_profile, 'Details')
    assert not view.toolbar.configuration.item_enabled('Edit this Analysis Profile')

    # Flash error from collection
    view = navigate_to(default_host_profile.parent, 'All')
    row = view.entities.table.row(
        name=default_host_profile.name, description=default_host_profile.description
    )
    row[0].check()
    view.toolbar.configuration.item_select('Edit the selected Analysis Profiles')
    view.flash.assert_message('Sample Analysis Profile "{}" can not be edited'.
                              format(default_host_profile.name))


def test_analysis_profile_item_validation(analysis_profile_collection):
    """ Test to validate analysis profile items.

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/15h
    """
    profile_name = fauxfactory.gen_alphanumeric()

    with pytest.raises(AssertionError):
        analysis_profile_collection.create(
            name=profile_name,
            description=profile_name,
            profile_type=analysis_profile_collection.HOST_TYPE
        )

    # Should still be on the form page after create method raises exception
    view = analysis_profile_collection.create_view(
        navigator.get_class(analysis_profile_collection, 'AddHostProfile').VIEW, wait='10s'
    )
    view.flash.assert_message("At least one item must be entered to create Analysis Profile")
    view.cancel.click()


def test_analysis_profile_name_validation(analysis_profile_collection):
    """ Test to validate profile name.

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/20h
    """

    with pytest.raises(AssertionError):
        analysis_profile_collection.create(
            name="",
            description=fauxfactory.gen_alphanumeric(),
            profile_type=analysis_profile_collection.HOST_TYPE,
            files=files_list
        )

    # Should still be on the form page after create method raises exception
    view = analysis_profile_collection.create_view(
        navigator.get_class(analysis_profile_collection, 'AddHostProfile').VIEW, wait='10s'
    )
    view.flash.assert_message("Name can't be blank")
    view.cancel.click()


@pytest.mark.ignore_stream('5.10')
def test_analysis_profile_description_validation(analysis_profile_collection):
    """ Test to validate profile description.

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
    """
    with pytest.raises(AssertionError):
        analysis_profile_collection.create(
            name=fauxfactory.gen_alphanumeric(),
            description="",
            profile_type=analysis_profile_collection.HOST_TYPE,
            files=files_list
        )

    # Should still be on the form page after create method raises exception
    view = analysis_profile_collection.create_view(
        navigator.get_class(analysis_profile_collection, 'AddHostProfile').VIEW, wait='10s'
    )
    view.flash.assert_message("Description can't be blank")
    view.cancel.click()


@test_requirements.rbac
@pytest.mark.tier(1)
@pytest.mark.ignore_stream('5.9')
@pytest.mark.parametrize(
    'product_features',
    [  # Navigation for product features trees
        # product_features tree for Managing Quotas for 'My Company' tenant
        [(['Everything', 'Settings', 'Configuration', 'Access Control', 'Tenants', 'Modify',
           'Manage Quotas', 'Manage Quotas (My Company)'], False)],
        # product_features tree for Managing Quotas for custom tenant
        [(['Everything', 'Settings', 'Configuration', 'Access Control', 'Tenants', 'Modify',
           'Manage Quotas', 'Manage Quotas ({})'.format(TENANT_NAME)], False)],
        # product_features tree for Managing Dialogs for 'Add'
        [(['Everything', 'Automation', 'Automate', 'Customization', 'Dialogs', 'Modify', 'Add',
           'Add ({})'.format(TENANT_NAME)], False)],
        # product_features tree for Managing Dialogs for 'Edit'
        [(['Everything', 'Automation', 'Automate', 'Customization', 'Dialogs', 'Modify', 'Edit',
           'Edit ({})'.format(TENANT_NAME)], False)],
        # product_features tree for Managing Dialogs for 'Delete'
        [(['Everything', 'Automation', 'Automate', 'Customization', 'Dialogs', 'Modify', 'Delete',
           'Delete ({})'.format(TENANT_NAME)], False)],
        # product_features tree for Managing Dialogs for  'Copy'
        [(['Everything', 'Automation', 'Automate', 'Customization', 'Dialogs', 'Modify', 'Copy',
           'Copy ({})'.format(TENANT_NAME)], False)]
    ]
)
def test_custom_role_modify_for_dynamic_product_feature(request, appliance, product_features):
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
            4. Or Update newly created custom role by doing uncheck in to options provided under
               Settings > Configuration > Access Control > Tenants > Modify > Manage Quotas
               > uncheck for any tenant
            5. You will see save button is not enabled but if you changed 'Name' or
               'Access Restriction for Services, VMs, and Templates' then save button is getting
               enabled.
            6. It updates changes only when we checked or unchecked for all of the tenants under
               edit/add/copy/delete options.

    Bugzilla:
        1655012
    """
    tenant = appliance.collections.tenants.create(
        name=TENANT_NAME,
        description="tenant_des{}".format(fauxfactory.gen_alphanumeric()),
        parent=appliance.collections.tenants.get_root_tenant(),
    )
    request.addfinalizer(tenant.delete)
    role = appliance.collections.roles.instantiate(name='EvmRole-tenant_quota_administrator')
    copied_role = role.copy()
    request.addfinalizer(copied_role.delete)
    view = navigate_to(copied_role, 'Details')

    # Checks whether feature tree path is checked for given node
    assert not view.features_tree.check_uncheck_node(True, *(product_features[0][0]))
    copied_role.update({'product_features': product_features})

    # Checks whether feature tree path is unchecked for given node
    assert view.features_tree.check_uncheck_node(True, *(product_features[0][0]))
