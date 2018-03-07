import fauxfactory
import pytest
from datetime import datetime, timedelta

from cfme.base.ui import BaseLoggedInPage
from cfme.utils.update import update

@pytest.fixture
def current_time():
    return datetime.utcnow()

def round_min(value, base=5):
    return int(base * round(float(value)/base))


def test_schedule_crud(appliance, current_time):
    start_date = current_time + timedelta(days=3)
    schedule = appliance.collections.system_schedules.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        start_date=start_date
    )

    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_message('Schedule "{}" was saved'.format(schedule.name))
    # test for bz
    start_date_updated = start_date - timedelta(days=1)
    updates = {
        'name': fauxfactory.gen_alphanumeric(),
        'description': fauxfactory.gen_alphanumeric(),
        }
    schedule.update(updates, cancel=True)
    view.flash.assert_message('Edit of Schedule "{}" was cancelled by the user'.format(
        schedule.name))
    schedule.update(updates, reset=True)
    view.flash.assert_message('All changes have been reset')
    with update(schedule):
        schedule.name = fauxfactory.gen_alphanumeric()
        schedule.start_date = start_date_updated
    view.flash.assert_message('Schedule "{}" was saved'.format(schedule.name))
    schedule.delete(cancel=True)
    schedule.delete()
    view.flash.assert_message('Schedule "{}": Delete successful'.format(schedule.description))


def test_schedule_analysis_in_the_past(appliance, current_time, request):
    past_time = current_time - timedelta(minutes=5)
    schedule = appliance.collections.system_schedules.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        start_hour=str(past_time.hour),
        start_minute=str(past_time.minute)
    )
    request.addfinalizer(schedule.delete)
    view = appliance.browser.create_view(BaseLoggedInPage)
    assert (
        "Warning: This 'Run Once' timer is in the past and will never"
        " run as currently configured" in [message.text for message in view.flash.messages]
    )


def test_create_multiple_schedules_in_one_timezone(appliance, request):
    schedule_list = []
    request.addfinalizer(lambda: map(lambda item: item.delete(), schedule_list))

    for i in range(6):
        schedule = appliance.collections.system_schedules.create(
            name=fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
            time_zone='(GMT-04:00) Atlantic Time (Canada)'
        )
        view = appliance.browser.create_view(BaseLoggedInPage)
        view.flash.assert_message('Schedule "{}" was saved'.format(schedule.name))
        schedule_list.append(schedule)


def test_inactive_schedule(appliance, current_time):
    start_date = current_time + timedelta(minutes=5)

    schedule = appliance.collections.system_schedules.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        start_date=start_date,
        start_hour=str(start_date.hour),
        start_minute=str(round_min(start_date.minute)),

    )
    assert schedule.next_run_date
    schedule.disable()
    assert not schedule.next_run_date

