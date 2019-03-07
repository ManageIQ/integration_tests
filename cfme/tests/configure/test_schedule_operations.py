import logging
import math
from datetime import datetime
from datetime import timedelta

import fauxfactory
import pytest
import pytz
from dateutil import parser
from dateutil import relativedelta

from cfme.base.ui import BaseLoggedInPage
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update
from cfme.utils.wait import wait_for

logger = logging.getLogger('cfme')

pytestmark = [
    pytest.mark.provider([VMwareProvider], required_fields=['hosts'], selector=ONE, scope='module'),
    pytest.mark.usefixtures("setup_provider")
]

run_types = (
    ['Once', None, None],
    ['Hourly', 'hours', 1],
    ['Daily', 'days', 1],
    ['Weekly', 'weeks', 1],
    ['Monthly', 'months', 1]
)


@pytest.fixture(scope='module')
def host_with_credentials(appliance, provider):
    """ Add credentials to hosts """
    host = provider.hosts.all()[0]
    host_data, = [data for data in provider.data['hosts'] if data['name'] == host.name]
    host.update_credentials_rest(credentials=host_data['credentials'])
    yield host
    host.remove_credentials_rest()


@pytest.fixture
def current_server_time(appliance):
    current_time = parser.parse(appliance.ssh_client.run_command('date --utc').output)
    tz_list = appliance.ssh_client.run_command("timedatectl | grep 'Time zone'") \
        .output.strip().split(' ')

    tz_name = tz_list[2]
    tz_num = tz_list[-1][:-1]
    #date = current_time.replace(tzinfo=pytz.timezone(tz_name))
    return current_time, tz_num


def round_min(value, base=5):
    return (0 if int(base * round(float(value) / base)) == 60
            else int(base * round(float(value) / base)))


def round_min2(value, base=5):
    minutes =  int(base * round(float(value.minute) / base))
    if minutes == 60:
        value += timedelta(hours=1)
        minutes = 0
    return value.replace(minute=minutes)


def ceil_min2(value, base=5):
    minutes =  int(base * math.ceil(float(value.minute) / base))
    if minutes == 60:
        value += timedelta(hours=1)
        minutes = 0
    return value.replace(minute=minutes)


def test_schedule_crud(appliance, current_server_time):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        initialEstimate: 1/16h
        caseimportance: high
    """
    current_time, _ = current_server_time
    start_date = current_time + relativedelta.relativedelta(days=2)
    schedule = appliance.collections.system_schedules.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        start_date=start_date
    )

    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_message('Schedule "{}" was saved'.format(schedule.name))
    # test for bz 1569127
    start_date_updated = start_date - relativedelta.relativedelta(days=1)
    updates = {
        'name': fauxfactory.gen_alphanumeric(),
        'description': fauxfactory.gen_alphanumeric(),
    }
    schedule.update(updates, cancel=True)
    view.flash.assert_message(
        'Edit of Schedule "{}" was cancelled by the user'.format(schedule.name))
    schedule.update(updates, reset=True)
    view.flash.assert_message('All changes have been reset')
    with update(schedule):
        schedule.name = fauxfactory.gen_alphanumeric()
        schedule.start_date = start_date_updated
    view.flash.assert_message('Schedule "{}" was saved'.format(schedule.name))
    schedule.delete(cancel=True)
    schedule.delete()
    view.flash.assert_message('Schedule "{}": Delete successful'.format(schedule.description))


def test_schedule_analysis_in_the_past(appliance, current_server_time, request):
    """
    Polarion:
        assignee: jhenner
        caseimportance: high
        initialEstimate: 1/4h
    """
    current_time, _ = current_server_time
    past_time = current_time - relativedelta.relativedelta(minutes=5)
    past_time = round_min2(past_time)
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
    """
    Polarion:
        assignee: jhenner
        caseimportance: high
        initialEstimate: 1/4h
    """
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


def test_inactive_schedule(appliance, current_server_time):
    """
    Polarion:
        assignee: jhenner
        caseimportance: high
        initialEstimate: 1/4h
    """
    current_time, _ = current_server_time
    start_date = current_time + relativedelta.relativedelta(minutes=5)
    start_date = round_min2(start_date)

    schedule = appliance.collections.system_schedules.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        start_date=start_date,
        start_hour=str(start_date.hour),
        start_minute=str(start_date.minute),

    )
    assert schedule.next_run_date
    schedule.disable()
    assert not schedule.next_run_date


def set_appliance_time(appliance, the_time):
    the_time = the_time.astimezone(pytz.utc)
    appliance.ssh_client.run_command("date -u {}".format(the_time.strftime('%m%d%H%M%Y')))


@pytest.mark.parametrize('run_types', run_types, ids=[type[0] for type in run_types])
def test_schedule_timer(appliance, run_types, host_with_credentials, request):
    """
    Polarion:
        assignee: jhenner
        caseimportance: high
        initialEstimate: 1/4h
    """
    run_time, time_diff, time_num = run_types
    # Set the appliance date and time to something without DST.
    initial_time = datetime(2019, 4, 6, 14, 2, 0, tzinfo=pytz.timezone('Europe/Prague'))
    set_appliance_time(appliance, initial_time)
    logger.debug('initial_time %s', initial_time)

    view = navigate_to(appliance.collections.system_schedules, 'Add')
    # bz is here 1559904
    available_list = view.form.time_zone.all_options
    current_time, _ = current_server_time(appliance)
    logger.debug('current_time %s', current_time)

    tz_select = '(GMT+01:00) Prague'
    # Allow sime time extra for filling the Schedule
    start_date = current_time + timedelta(minutes=2)
    start_date = start_date.astimezone(pytz.timezone('Europe/Prague'))
    start_date = ceil_min2(start_date)
    logger.debug('start_date %s', start_date)

    schedule = appliance.collections.system_schedules.create(
        name=fauxfactory.gen_alphanumeric(),
        description='{} {}'.format(fauxfactory.gen_alphanumeric(),
                                   start_date.isoformat()),
        action_type='Host Analysis',
        filter_level1='A single Host',
        filter_level2=host_with_credentials.name,
        run_type=run_time,
        start_date=start_date,
        time_zone=tz_select, start_hour=str(start_date.hour),
        start_minute=str(start_date.minute),
    )

    current_time2, _ = current_server_time(appliance)
    time_buffer = (start_date - current_time2).total_seconds()
    logger.info('Will have to wait %d:%d for the schedule to fire up.', time_buffer // 60, time_buffer % 60)
    assert current_time2 < start_date, (
            'Adding the schedule took too long time ({} extra seconds).'.format(time_buffer))

    @request.addfinalizer
    def _finalize():
        if schedule.exists:
            schedule.delete()

    logger.debug('Waiting for first run to finish.')
    wait_for(lambda: schedule.last_run_date != '',
             delay=10, timeout="10m", fail_func=appliance.server.browser.refresh,
             message="Scheduled task didn't run in first time")

    if time_diff:
        next_date = parser.parse(schedule.next_run_date)
        up = {time_diff: time_num}
        next_run_date = start_date + relativedelta.relativedelta(minutes=-3, **up)
        set_appliance_time(appliance, next_run_date)
        logger.debug('next_run_date %s', next_run_date)

        wait_for(
            lambda: abs(next_date - parser.parse(schedule.last_run_date)) < timedelta(minutes=1),
            delay=10, timeout="10m", fail_func=appliance.server.browser.refresh,
            message="Scheduled task didn't run in appropriate time set")
