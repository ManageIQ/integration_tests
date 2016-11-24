# -*- coding: utf-8 -*-
import fauxfactory
import cfme.configure.settings as st
import pytest
import utils.error as error
from utils.blockers import BZ
from utils.update import update
from utils import version
from cfme import test_requirements
from cfme.web_ui import form_buttons

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings]


def new_timeprofile():
    return st.Timeprofile(description='time_profile' + fauxfactory.gen_alphanumeric(),
                          scope='Current User',
                          days=True,
                          hours=True,
                          timezone="(GMT-10:00) Hawaii")


@pytest.mark.sauce
def test_timeprofile_crud():
    timeprofile = new_timeprofile()
    timeprofile.create()
    with update(timeprofile):
        timeprofile.scope = 'All Users'
    copied_timeprofile = timeprofile.copy()
    copied_timeprofile.delete()
    timeprofile.delete()


@pytest.mark.meta(blockers=[BZ(1394833, forced_streams=["5.7", "upstream"])])
@pytest.mark.sauce
def test_timeprofile_duplicate_name():
    nt = new_timeprofile()
    nt.create()
    msg = "Error during 'add': Validation failed: Description has already been taken"
    with error.expected(msg):
        nt.create()
    nt.delete()


@pytest.mark.sauce
def test_timeprofile_name_max_character_validation():
    tp = st.Timeprofile(
        description=fauxfactory.gen_alphanumeric(50),
        scope='Current User',
        timezone="(GMT-10:00) Hawaii")
    tp.create()
    tp.delete()


@pytest.mark.sauce
def test_days_required_error_validation():
    tp = st.Timeprofile(
        description='time_profile' + fauxfactory.gen_alphanumeric(),
        scope='Current User',
        timezone="(GMT-10:00) Hawaii",
        days=False,
        hours=True)
    if version.current_version() > "5.7":
        tp.create(cancel=True)
        assert "At least one day needs to be selected" == \
               tp.timeprofile_form.days.angular_help_block
        assert form_buttons.add.is_dimmed
    else:
        with error.expected("At least one Day must be selected"):
            tp.create()


@pytest.mark.sauce
def test_hours_required_error_validation():
    tp = st.Timeprofile(
        description='time_profile' + fauxfactory.gen_alphanumeric(),
        scope='Current User',
        timezone="(GMT-10:00) Hawaii",
        days=True,
        hours=False)
    if version.current_version() > "5.7":
        tp.create(cancel=True)
        assert "At least one hour needs to be selected" == \
               tp.timeprofile_form.days.angular_help_block
        assert form_buttons.add.is_dimmed
    else:
        with error.expected("At least one Hour must be selected"):
            tp.create()


@pytest.mark.sauce
def test_description_required_error_validation():
    tp = st.Timeprofile(
        description=None,
        scope='Current User',
        timezone="(GMT-10:00) Hawaii")
    if version.current_version() > "5.7":
        tp.create(cancel=True)
        assert tp.timeprofile_form.description.angular_help_block == "Required"
        assert form_buttons.add.is_dimmed
    else:
        with error.expected("Description is required"):
            tp.create()
