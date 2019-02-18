# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import yaml

from cfme import test_requirements
from cfme.intelligence.reports.schedules import NewScheduleView
from cfme.intelligence.reports.schedules import ScheduleDetailsView
from cfme.utils.path import data_path

pytestmark = [test_requirements.report, pytest.mark.tier(3), pytest.mark.sauce]

schedules_report_dir = data_path.join("schedules_crud")


TIMER = {
    "monthly": {"run": "Monthly", "hours": "Month"},
    "hourly": {"run": "Hourly", "hours": "Hour"},
    "daily": {"run": "Daily", "hours": "Day"},
    "weekly": {"run": "Weekly", "hours": "Week"},
    "once": {"run": "Once", "hours": ""},
}


def schedule_files():
    result = []
    for file_name in schedules_report_dir.listdir():
        if file_name.isfile() and file_name.basename.endswith(".yaml"):
            result.append(file_name.basename)
    return result


@pytest.fixture(
    params=schedule_files(),
    ids=[schedule.split(".")[0] for schedule in schedule_files()],
)
def schedule_data(request, interval=None):
    with schedules_report_dir.join(request.param).open(mode="r") as rep_yaml:
        schedule_data = yaml.safe_load(rep_yaml)
        if interval:
            schedule_data["timer"] = TIMER[interval]
        yield schedule_data


@pytest.fixture(scope="function")
def schedule(schedule_data, appliance):
    collection = appliance.collections.schedules
    schedule = collection.create(**schedule_data)
    yield schedule
    if schedule.exists:
        schedule.delete()


@pytest.mark.parametrize("interval", TIMER)
def test_schedule_queue(schedule, appliance, interval):
    """ To test scheduling of report using options: Once, Hourly, Daily, Weekly, Monthly

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/10h
        tags: report
    """

    schedule.queue()
    view = schedule.create_view(ScheduleDetailsView)
    view.flash.assert_message("The selected Schedule has been queued to run")


def test_reports_disable_enable_schedule(appliance, schedule):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/10h
        tags: report
    """
    schedules = appliance.collections.schedules
    schedules.disable_schedules(schedule)
    assert not schedule.enabled
    schedules.enable_schedules(schedule)
    assert schedule.enabled


@pytest.mark.ignore_stream("5.9")
def test_report_schedules_invalid_email(appliance, schedule_data):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/12h
        tags: report
    """
    schedule_data["emails"] = (fauxfactory.gen_alpha(), fauxfactory.gen_alpha())
    schedule_data["from_email"] = fauxfactory.gen_alpha()
    with pytest.raises(AssertionError):
        appliance.collections.schedules.create(**schedule_data)
    view = appliance.collections.schedules.create_view(NewScheduleView)
    view.flash.assert_message("One of e-mail addresses 'To' is not valid")
    view.flash.assert_message("E-mail address 'From' is not valid")
