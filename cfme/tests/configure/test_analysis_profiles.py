# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.configure.configuration.analysis_profile import AnalysisProfile, AnalysisProfileAddView
from cfme.utils.blockers import BZ
from cfme.utils.appliance.implementations.ui import navigate_to
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


@pytest.yield_fixture(scope='module')
def vm_profile():
    return AnalysisProfile(name=fauxfactory.gen_alphanumeric(),
                           description=fauxfactory.gen_alphanumeric(),
                           profile_type=AnalysisProfile.VM_TYPE,
                           files=files_list, categories=categories_list, registry=registry_list,
                           events=events_check())


@pytest.yield_fixture(scope='module')
def host_profile():
    return AnalysisProfile(name=fauxfactory.gen_alphanumeric(),
                           description=fauxfactory.gen_alphanumeric(),
                           profile_type=AnalysisProfile.HOST_TYPE,
                           files=files_list, events=events_check())


@pytest.mark.tier(2)
def test_vm_analysis_profile_crud(soft_assert, vm_profile):
    """CRUD for VM analysis profiles."""
    vm_profile.create()
    assert vm_profile.exists

    files_updates = events_check(updates=True)
    with update(vm_profile):
        vm_profile.files = files_updates
    soft_assert(vm_profile.files == files_updates,
                'Files update failed on profile: {}, {}'.format(vm_profile.name, vm_profile.files))

    with update(vm_profile):
        vm_profile.categories = ['System']
    soft_assert(vm_profile.categories == ['System'],
                'Categories update failed on profile: {}'.format(vm_profile.name))

    copied_profile = vm_profile.copy(new_name='copied-{}'.format(vm_profile.name))
    assert copied_profile.exists

    copied_profile.delete()
    assert not copied_profile.exists

    vm_profile.delete()
    assert not vm_profile.exists


@pytest.mark.tier(2)
def test_host_analysis_profile_crud(soft_assert, host_profile):
    """CRUD for Host analysis profiles."""
    host_profile.create()
    assert host_profile.exists

    files_updates = events_check(updates=True)
    with update(host_profile):
        host_profile.files = files_updates
    soft_assert(host_profile.files == files_updates,
                'Files update failed on profile: {}, {}'
                .format(host_profile.name, host_profile.files))

    copied_profile = host_profile.copy(new_name='copied-{}'.format(host_profile.name))
    assert copied_profile.exists

    copied_profile.delete()
    assert not copied_profile.exists

    host_profile.delete()
    assert not host_profile.exists


# TODO Combine and parametrize VM + Host validation tests
# Parametrize VM/Host, and (name/description/no item + flash) message as namedtuple
def test_vmanalysis_profile_description_validation():
    """ Test to validate description in vm profiles"""
    profile = AnalysisProfile(name=fauxfactory.gen_alphanumeric(), description=None,
                              profile_type=AnalysisProfile.VM_TYPE,
                              categories=categories_list)
    with pytest.raises(AssertionError):
        profile.create()

    # Should still be on the form page after create method raises exception
    view = profile.create_view(AnalysisProfileAddView)
    assert view.is_displayed
    view.flash.assert_message("Description can't be blank")
    view.cancel.click()


def test_analysis_profile_duplicate_name():
    """ Test to validate duplicate profiles name."""
    profile = AnalysisProfile(name=fauxfactory.gen_alphanumeric(),
                              description=fauxfactory.gen_alphanumeric(),
                              profile_type=AnalysisProfile.VM_TYPE,
                              categories=categories_list)
    profile.create()

    with pytest.raises(AssertionError):
        profile.create()

    # Should still be on the form page after create method raises exception
    view = profile.create_view(AnalysisProfileAddView)
    assert view.is_displayed
    view.flash.assert_message("Name has already been taken")
    view.cancel.click()


def test_delete_default_analysis_profile():
    """ Test to validate delete default profiles."""
    profile = AnalysisProfile(name="host sample", description='Host Sample',
                              profile_type=AnalysisProfile.HOST_TYPE)
    # Option disabled from details
    view = navigate_to(profile, 'Details')
    assert not view.toolbar.configuration.item_enabled('Delete this Analysis Profile')

    # Flash error from collection
    view = navigate_to(profile, 'All')
    row = view.entities.table.row(name=profile.name, description=profile.description)
    row[0].check()
    view.toolbar.configuration.item_select('Delete the selected Analysis Profiles',
                                           handle_alert=True)
    view.flash.assert_message('Default Analysis Profile "{}" can not be deleted'
                              .format(profile.name))


def test_edit_default_analysis_profile():
    """ Test to validate edit default profiles."""
    profile = AnalysisProfile(name="host sample", description='Host Sample',
                              profile_type=AnalysisProfile.HOST_TYPE)
    # Option disabled from details
    view = navigate_to(profile, 'Details')
    assert not view.toolbar.configuration.item_enabled('Edit this Analysis Profile')

    # Flash error from collection
    view = navigate_to(profile, 'All')
    row = view.entities.table.row(name=profile.name, description=profile.description)
    row[0].check()
    view.toolbar.configuration.item_select('Edit the selected Analysis Profiles')
    view.flash.assert_message('Sample Analysis Profile "{}" can not be edited'.format(profile.name))


def test_analysis_profile_item_validation():
    """ Test to validate analysis profile items."""
    profile_name = fauxfactory.gen_alphanumeric()
    profile = AnalysisProfile(name=profile_name, description=profile_name,
                              profile_type=AnalysisProfile.HOST_TYPE)

    with pytest.raises(AssertionError):
        profile.create()

    # Should still be on the form page after create method raises exception
    view = profile.create_view(AnalysisProfileAddView)
    assert view.is_displayed
    view.flash.assert_message("At least one item must be entered to create Analysis Profile")
    view.cancel.click()


def test_analysis_profile_name_validation():
    """ Test to validate profile name."""
    profile = AnalysisProfile(name="", description=fauxfactory.gen_alphanumeric(),
                              profile_type=AnalysisProfile.HOST_TYPE, files=files_list)
    with pytest.raises(AssertionError):
        profile.create()

    # Should still be on the form page after create method raises exception
    view = profile.create_view(AnalysisProfileAddView)
    assert view.is_displayed
    view.flash.assert_message("Name can't be blank")
    view.cancel.click()


def test_analysis_profile_description_validation():
    """ Test to validate profile description."""
    profile = AnalysisProfile(name=fauxfactory.gen_alphanumeric(), description="",
                              profile_type=AnalysisProfile.HOST_TYPE, files=files_list)
    with pytest.raises(AssertionError):
        profile.create()

    # Should still be on the form page after create method raises exception
    view = profile.create_view(AnalysisProfileAddView)
    assert view.is_displayed
    view.flash.assert_message("Description can't be blank")
    view.cancel.click()
