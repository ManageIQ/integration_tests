# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import yaml

from cfme import test_requirements
from cfme.intelligence.reports.schedules import NewScheduleView
from cfme.intelligence.reports.schedules import ScheduleDetailsView
from cfme.rest.gen_data import users as _users
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.path import data_path
from cfme.utils.wait import wait_for

pytestmark = [test_requirements.report, pytest.mark.tier(3), pytest.mark.sauce]

SCHEDULES_REPORT_DIR = data_path.join("schedules_crud")


TIMER = {
    "monthly": {
        "run": "Monthly",
        "timer_month": "2 Months",
        "hour": "12",
        "minute": "5",
        "time_zone": "(GMT+10:00) Melbourne",
    },
    "hourly": {
        "run": "Hourly",
        "timer_hour": "6 Hours",
        "hour": "12",
        "minute": "5",
        "time_zone": "(GMT+10:00) Melbourne",
    },
    "daily": {
        "run": "Daily",
        "timer_day": "2 Days",
        "hour": "12",
        "minute": "5",
        "time_zone": "(GMT+10:00) Melbourne",
    },
    "weekly": {
        "run": "Weekly",
        "timer_week": "3 Weeks",
        "hour": "12",
        "minute": "5",
        "time_zone": "(GMT+10:00) Melbourne",
    },
    "once": {
        "run": "Once",
        "hour": "12",
        "minute": "5",
        "time_zone": "(GMT+10:00) Melbourne",
    },
}

INVALID_EMAILS = {
    "string": fauxfactory.gen_alpha(),
    "multiple-dots": "{name}..{name}@example..com".format(
        name=fauxfactory.gen_alpha(5)
    ),
    "brackets": "{name}@example.com({name})".format(name=fauxfactory.gen_alpha(5)),
    "leading-dot": ".{name}@example.com".format(name=fauxfactory.gen_alpha(5)),
    "dash": "{name}@-example.com".format(name=fauxfactory.gen_alpha(5)),
    "missing-@": "{name}.example.com".format(name=fauxfactory.gen_alpha(5)),
    "trailing-dot": "{name}.@example.com".format(name=fauxfactory.gen_alpha(5)),
    "missing-username": "@example.com",
}


def schedule_files():
    result = []
    if not SCHEDULES_REPORT_DIR.exists:
        SCHEDULES_REPORT_DIR.mkdir()
    for file_name in SCHEDULES_REPORT_DIR.listdir():
        if file_name.isfile() and file_name.basename.endswith(".yaml"):
            result.append(file_name.basename)
    return result


@pytest.fixture(
    params=schedule_files(),
    ids=[schedule.split(".")[0] for schedule in schedule_files()],
)
def schedule_data(request):
    with SCHEDULES_REPORT_DIR.join(request.param).open(mode="r") as rep_yaml:
        return yaml.safe_load(rep_yaml)


@pytest.fixture(scope="function")
def schedule(schedule_data, appliance):
    schedule = appliance.collections.schedules.create(**schedule_data)
    yield schedule
    schedule.delete_if_exists()


@pytest.fixture
def user(appliance, request):
    users, user_data = _users(
        request,
        appliance,
        name="Sherlock Holmes",
        email="shholmes@redhat.com",
        userid="shholmes",
        password="smartvm",
        group="EvmGroup-super_administrator",
    )

    return users[0]


@pytest.mark.parametrize("interval", TIMER)
def test_schedule_queue(appliance, request, interval, schedule_data):
    """ To test scheduling of report using options: Once, Hourly, Daily, Weekly, Monthly

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/10h
        tags: report
    """
    schedule_data["timer"] = TIMER[interval]
    schedule = appliance.collections.schedules.create(**schedule_data)
    request.addfinalizer(schedule.delete_if_exists)

    schedule.queue()
    assert schedule.timer == TIMER[interval]
    view = schedule.create_view(ScheduleDetailsView)
    view.flash.assert_message("The selected Schedule has been queued to run")


@pytest.mark.parametrize("email", INVALID_EMAILS)
def test_report_schedules_invalid_email(appliance, schedule_data, email):
    """
    This test case checks if invalid emails are accepted while creating a schedule

    TODO: In addition to above patterns, there are few invalid patterns which are still accepted.
    Patterns such as: xyz@example@example.com, xyz@example, ?/><!$%@example.com
    BZ(1684491) has been filed for this.

    Bugzilla:
        1684491

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/12h
        tags: report
    """
    schedule_data["email"]["to_emails"] = schedule_data["email"][
        "from_email"
    ] = INVALID_EMAILS[email]
    with pytest.raises(AssertionError):
        appliance.collections.schedules.create(**schedule_data)
    view = appliance.collections.schedules.create_view(NewScheduleView)
    view.flash.assert_message("One of e-mail addresses 'To' is not valid")
    view.flash.assert_message("E-mail address 'From' is not valid")


@pytest.mark.tier(1)
@pytest.mark.meta(server_roles="+notifier")
def test_reports_create_schedule_send_report(smtp_test, schedule):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
        tags: report
        setup:
            1. Navigate to Cloud > Intel > Reports > Schedules.
            2. Click on `Configuration` and select `Add a new Schedule`.
            3. Create schedule that send an email to more than one users.
            Un-check "Send if Report is Empty" option.
        testSteps:
            1. Queue up this Schedule and check if the email was sent.
        expectedResults:
            1. Queueing the schedule must send the report via email to all the users.
    """
    schedule.queue()
    emails_sent = ",".join(schedule.email.get("to_emails", []))
    # take initial count of sent emails in account
    initial_count = len(smtp_test.get_emails())
    # wait for emails to appear
    wait_for(lambda: len(smtp_test.get_emails()) > initial_count, num_sec=90, delay=5)

    assert len(smtp_test.get_emails(to_address=emails_sent)) == 1


def test_reports_disable_enable_schedule(appliance, schedule):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/10h
        tags: report
    """
    schedules = appliance.collections.schedules
    schedules.disable_schedules(schedule)
    assert not schedule.enabled
    schedules.enable_schedules(schedule)
    assert schedule.enabled


@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(automates=[1559335])
def test_reports_disable_enable_schedule_from_summary(appliance, schedule):
    """
    This test checks if schedule can be enabled/disabled from it's summary page.

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/10h

    Bugzilla:
        1559335
    """
    view = navigate_to(schedule, "Details")
    view.configuration.item_select("Disable this Schedule")
    assert not schedule.enabled
    # enabled directs to Schedules `All` page, we need to navigate back to Details page
    navigate_to(schedule, "Details")
    view.configuration.item_select("Enable this Schedule")
    assert schedule.enabled


def test_reports_schedules_user(appliance, request, user, schedule_data):
    """
    This test checks if a user is visible under the Emails options of schedule form
    while creating a schedule

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/10h
        setup:
            1. Create a user with an email belonging to the same group as logged in user.
        testSteps:
            1. Create a schedule and check if the newly created user is available
            under `User` dropdown.
    """
    schedule_data["email"] = {"user_email": f"{user.name} ({user.email})"}
    schedule = appliance.collections.schedules.create(**schedule_data)
    request.addfinalizer(schedule.delete)
    assert schedule.exists
    view = schedule.create_view(ScheduleDetailsView)
    assert view.schedule_info.get_text_of("To E-mail") == f"{user.name} ({user.email})"
