# -*- coding: utf-8 -*-

import cfme.configure.settings as st
import utils.randomness as random
from utils.update import update


def new_timeprofile():
    return st.Timeprofile(description='time_profile' + random.generate_random_string(),
                   scope='Current User',
                   timezone="(GMT-10:00) Hawaii")


def test_timeprofile_add():
    timeprofile = new_timeprofile()
    timeprofile.create()
    with update(timeprofile):
        timeprofile.scope = 'All Users'
    copied_timeprofile = timeprofile.copy()
    copied_timeprofile.delete()
    timeprofile.delete()
