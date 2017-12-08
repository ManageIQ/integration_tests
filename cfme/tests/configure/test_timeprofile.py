# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.configure.settings import TimeProfileAddFormView
from cfme.utils.update import update
from cfme import test_requirements

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings]


@pytest.mark.sauce
def test_time_profile_crud(appliance):
    """
        This test case performs the CRUD operation.
    """
    collection = appliance.collections.time_profiles
    time_profile = collection.create(description='time_profile' + fauxfactory.gen_alphanumeric(),
                                     scope='Current User',
                                     days=True, hours=True,
                                     timezone="(GMT-10:00) Hawaii")
    with update(time_profile):
        time_profile.scope = 'All Users'
        collection.delete(False, time_profile)


@pytest.mark.sauce
def test_time_profile_name_max_character_validation(appliance):
    """
    This test case performs the check for max character validation.
    """
    collection = appliance.collections.time_profiles
    time_profile = collection.create(
        description=fauxfactory.gen_alphanumeric(50),
        scope='Current User',
        timezone="(GMT-10:00) Hawaii")
    collection.delete(False, time_profile)


@pytest.mark.sauce
def test_days_required_error_validation(appliance, soft_assert):
    """
    This test case performs the error validation of days field.
    """
    collection = appliance.collections.time_profiles
    collection.create(
        description='time_profile' + fauxfactory.gen_alphanumeric(),
        scope='Current User',
        timezone="(GMT-10:00) Hawaii",
        days=False,
        hours=True,
        cancel=True)
    view = appliance.browser.create_view(TimeProfileAddFormView)
    soft_assert(view.timeprofile_form.help_block.text == "At least one day needs to be selected")
    soft_assert(view.timeprofile_form.save_button.disabled)
    view.timeprofile_form.cancel_button.click()


@pytest.mark.sauce
def test_hours_required_error_validation(appliance, soft_assert):
    """
    This test case performs the error validation of hours field.
    """
    collection = appliance.collections.time_profiles
    collection.create(
        description='time_profile' + fauxfactory.gen_alphanumeric(),
        scope='Current User',
        timezone="(GMT-10:00) Hawaii",
        days=True,
        hours=False,
        cancel=True)
    view = appliance.browser.create_view(TimeProfileAddFormView)
    soft_assert(view.timeprofile_form.help_block.text == "At least one hour needs to be selected")
    soft_assert(view.timeprofile_form.save_button.disabled)
    view.timeprofile_form.cancel_button.click()


@pytest.mark.sauce
def test_time_profile_description_required_error_validation(appliance, soft_assert):
    """
    This test case performs the error validation of description field.
    """
    collection = appliance.collections.time_profiles
    collection.create(
        description=None,
        scope='Current User',
        timezone="(GMT-10:00) Hawaii",
        cancel=True)
    view = appliance.browser.create_view(TimeProfileAddFormView)
    soft_assert(view.time_profile_form.description.help_block == "Required")
    soft_assert(view.time_profile_form.save_button.disabled)
    view.time_profile_form.cancel_button.click()


@pytest.mark.sauce
def test_time_profile_copy(appliance):
    """
    This test case checks the copy operation of the time_profile.
    """
    collection = appliance.collections.time_profiles
    time_profile = collection.create(description='time_profile' + fauxfactory.gen_alphanumeric(),
                                     scope='Current User',
                                     days=True,
                                     hours=True,
                                     timezone="(GMT-10:00) Hawaii")
    copied_time_profile = time_profile.copy()
    collection.delete(False, time_profile, copied_time_profile)
