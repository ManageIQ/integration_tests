# -*- coding: utf-8 -*-

import cfme.configure.settings as st
import utils.error as error
import utils.randomness as random
from utils.update import update


def new_timeprofile():
    return st.Timeprofile(description='time_profile' + random.generate_random_string(),
                   scope='Current User',
                   days=True,
                   hours=True,
                   timezone="(GMT-10:00) Hawaii")


def test_timeprofile_crud():
    timeprofile = new_timeprofile()
    timeprofile.create()
    with update(timeprofile):
        timeprofile.scope = 'All Users'
    copied_timeprofile = timeprofile.copy()
    copied_timeprofile.delete()
    timeprofile.delete()


def test_timeprofile_duplicate_name():
    nt = new_timeprofile()
    nt.create()
    msg = "Error during 'add': Validation failed: Description has already been taken"
    with error.expected(msg):
        nt.create()
    nt. delete()


def test_timeprofile_name_max_character_validation():
    tp = st.Timeprofile(
        description=random.generate_random_string(size=50),
        scope='Current User',
        timezone="(GMT-10:00) Hawaii")
    tp.create()
    tp.delete()


def test_days_required_error_validation():
    tp = st.Timeprofile(
        description='time_profile' + random.generate_random_string(),
        scope='Current User',
        timezone="(GMT-10:00) Hawaii",
        days=False,
        hours=True)
    with error.expected("At least one Day must be selected"):
        tp.create()


def test_hours_required_error_validation():
    tp = st.Timeprofile(
        description='time_profile' + random.generate_random_string(),
        scope='Current User',
        timezone="(GMT-10:00) Hawaii",
        days=True,
        hours=False)
    with error.expected("At least one Hour must be selected"):
        tp.create()


def test_description_required_error_validation():
    tp = st.Timeprofile(
        description=None,
        scope='Current User',
        timezone="(GMT-10:00) Hawaii")
    with error.expected("Description is required"):
        tp.create()
