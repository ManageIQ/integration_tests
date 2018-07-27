# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.utils.appliance.implementations.ui import navigate_to, navigator
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


def events_check(updates=False):
    form_bug = BZ(1485953, forced_streams=['5.7', '5.8', 'upstream'])
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
    """CRUD for VM analysis profiles."""
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
    if not BZ(1609206, forced_streams=['5.10']).blocks:
        view.flash.assert_message('Analysis Profile "{}" was saved'.format(vm_profile.name))

    assert vm_profile.exists

    files_updates = events_check(updates=True)
    with update(vm_profile):
        vm_profile.files = files_updates
    view = appliance.browser.create_view(navigator.get_class(vm_profile, 'Details').VIEW)
    if not BZ(1609206, forced_streams=['5.10']).blocks:
        view.flash.assert_success_message(
            'Analysis Profile "{}" was saved'.format(vm_profile.name))
    soft_assert(vm_profile.files == files_updates,
                'Files update failed on profile: {}, {}'.format(vm_profile.name, vm_profile.files))

    with update(vm_profile):
        vm_profile.categories = ['System']
    soft_assert(vm_profile.categories == ['System'],
                'Categories update failed on profile: {}'.format(vm_profile.name))
    pytest.set_trace()
    copied_profile = vm_profile.copy(new_name='copied-{}'.format(vm_profile.name))
    view = appliance.browser.create_view(
        navigator.get_class(analysis_profile_collection, 'All').VIEW)
    # yep, not copy specific
    if not BZ(1609206, forced_streams=['5.10']).blocks:
        view.flash.assert_message('Analysis Profile "{}" was saved'.format(copied_profile.name))
    assert copied_profile.exists

    copied_profile.delete()
    assert not copied_profile.exists

    vm_profile.delete()
    if not BZ(1609206, forced_streams=['5.10']).blocks:
        view.flash.assert_success_message(
            'Analysis Profile "{}": Delete successful'.format(vm_profile.name))
    assert not vm_profile.exists


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_host_analysis_profile_crud(appliance, soft_assert, analysis_profile_collection):
    """CRUD for Host analysis profiles."""
    host_profile = analysis_profile_collection.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        profile_type=analysis_profile_collection.HOST_TYPE,
        files=files_list,
        events=events_check()
    )
    view = appliance.browser.create_view(
        navigator.get_class(analysis_profile_collection, 'All').VIEW)
    if not BZ(1609206, forced_streams=['5.10']).blocks:
        view.flash.assert_message('Analysis Profile "{}" was saved'.format(host_profile.name))
    assert host_profile.exists

    files_updates = events_check(updates=True)
    with update(host_profile):
        host_profile.files = files_updates
    soft_assert(host_profile.files == files_updates,
                'Files update failed on profile: {}, {}'
                .format(host_profile.name, host_profile.files))
    pytest.set_trace()
    copied_profile = host_profile.copy(new_name='copied-{}'.format(host_profile.name))
    view = appliance.browser.create_view(
        navigator.get_class(analysis_profile_collection, 'All').VIEW)
    if not BZ(1609206, forced_streams=['5.10']).blocks:
        view.flash.assert_message('Analysis Profile "{}" was saved'.format(copied_profile.name))
    assert copied_profile.exists

    copied_profile.delete()
    assert not copied_profile.exists

    host_profile.delete()
    if not BZ(1609206, forced_streams=['5.10']).blocks:
        view.flash.assert_success_message(
            'Analysis Profile "{}": Delete successful'.format(host_profile.name))
    assert not host_profile.exists


# TODO Combine and parametrize VM + Host validation tests
# Parametrize VM/Host, and (name/description/no item + flash) message as namedtuple
def test_vmanalysis_profile_description_validation(analysis_profile_collection):
    """ Test to validate description in vm profiles"""
    with pytest.raises(AssertionError):
        analysis_profile_collection.create(
            name=fauxfactory.gen_alphanumeric(),
            description=None,
            profile_type=analysis_profile_collection.VM_TYPE,
            categories=categories_list
        )

    # Should still be on the form page after create method raises exception
    view = analysis_profile_collection.create_view(
        navigator.get_class(analysis_profile_collection, 'AddVmProfile').VIEW
    )
    assert view.is_displayed
    view.flash.assert_message("Description can't be blank")
    view.cancel.click()


def test_analysis_profile_duplicate_name(analysis_profile_collection):
    """ Test to validate duplicate profiles name."""
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
        navigator.get_class(analysis_profile_collection, 'AddVmProfile').VIEW
    )
    assert view.is_displayed
    view.flash.assert_message("Name has already been taken")
    view.cancel.click()


def test_delete_default_analysis_profile(default_host_profile):
    """ Test to validate delete default profiles."""
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
    if not BZ(1609206, forced_streams=['5.10']).blocks:
        view.flash.assert_message('Default Analysis Profile "{}" can not be deleted'
                                  .format(default_host_profile.name))


def test_edit_default_analysis_profile(default_host_profile):
    """ Test to validate edit default profiles."""
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
    if not BZ(1609206, forced_streams=['5.10']).blocks:
        view.flash.assert_message('Sample Analysis Profile "{}" can not be edited'.format(
            default_host_profile.name))


def test_analysis_profile_item_validation(analysis_profile_collection):
    """ Test to validate analysis profile items."""
    profile_name = fauxfactory.gen_alphanumeric()

    with pytest.raises(AssertionError):
        analysis_profile_collection.create(
            name=profile_name,
            description=profile_name,
            profile_type=analysis_profile_collection.HOST_TYPE
        )

    # Should still be on the form page after create method raises exception
    view = analysis_profile_collection.create_view(
        navigator.get_class(analysis_profile_collection, 'AddHostProfile').VIEW
    )
    assert view.is_displayed
    view.flash.assert_message("At least one item must be entered to create Analysis Profile")
    view.cancel.click()


def test_analysis_profile_name_validation(analysis_profile_collection):
    """ Test to validate profile name."""

    with pytest.raises(AssertionError):
        analysis_profile_collection.create(
            name="",
            description=fauxfactory.gen_alphanumeric(),
            profile_type=analysis_profile_collection.HOST_TYPE,
            files=files_list
        )

    # Should still be on the form page after create method raises exception
    view = analysis_profile_collection.create_view(
        navigator.get_class(analysis_profile_collection, 'AddHostProfile').VIEW
    )
    assert view.is_displayed
    view.flash.assert_message("Name can't be blank")
    view.cancel.click()


def test_analysis_profile_description_validation(analysis_profile_collection):
    """ Test to validate profile description."""
    with pytest.raises(AssertionError):
        analysis_profile_collection.create(
            name=fauxfactory.gen_alphanumeric(),
            description="",
            profile_type=analysis_profile_collection.HOST_TYPE,
            files=files_list
        )

    # Should still be on the form page after create method raises exception
    view = analysis_profile_collection.create_view(
        navigator.get_class(analysis_profile_collection, 'AddHostProfile').VIEW
    )
    assert view.is_displayed
    view.flash.assert_message("Description can't be blank")
    view.cancel.click()
