# -*- coding: utf-8 -*-
import pytest
import yaml

from cfme import test_requirements
from cfme.intelligence.reports.schedules import ScheduleDetailsView
from cfme.utils.path import data_path


schedules_report_dir = data_path.join("schedules_report")


def schedule_files():
    result = []
    for file_name in schedules_report_dir.listdir():
        if file_name.isfile() and file_name.basename.endswith(".yaml"):
            result.append(file_name.basename)
    return result


@pytest.fixture(params=schedule_files(),
                ids=[schedule.split(".")[0] for schedule in schedule_files()])
def schedule_data(request):
    with schedules_report_dir.join(request.param).open(mode="r") as rep_yaml:
        return yaml.safe_load(rep_yaml)


@pytest.fixture(scope='function')
def schedule(schedule_data, appliance):
    collection = appliance.collections.schedules
    schedule = collection.create(**schedule_data)
    yield schedule
    if schedule.exists:
        schedule.delete()


@pytest.mark.sauce
@pytest.mark.tier(3)
@test_requirements.report
def test_schedule_queue(schedule, appliance):
    """ To test scheduling of report using options: Once, Hourly, Daily, Weekly, Monthly

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: high
        initialEstimate: 1/10h
    """

    schedule.queue()
    view = schedule.create_view(ScheduleDetailsView)
    view.flash.assert_message('The selected Schedule has been queued to run')
