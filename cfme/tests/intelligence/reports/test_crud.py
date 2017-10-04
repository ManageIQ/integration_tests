# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import yaml

from cfme import test_requirements
from cfme.intelligence.reports.dashboards import Dashboard
from cfme.intelligence.reports.reports import CustomReport
from cfme.intelligence.reports.schedules import ScheduleCollection
from cfme.intelligence.reports.widgets.menu_widgets import MenuWidget
from cfme.intelligence.reports.widgets.report_widgets import ReportWidget
from cfme.intelligence.reports.widgets.chart_widgets import ChartWidget
from cfme.intelligence.reports.widgets.rss_widgets import RSSFeedWidget
from cfme.utils.blockers import BZ
from cfme.utils.path import data_path
from cfme.utils.update import update
from cfme.utils.wait import wait_for_decorator


report_crud_dir = data_path.join("reports_crud")
schedules_crud_dir = data_path.join("schedules_crud")


def crud_files_reports():
    result = []
    if not report_crud_dir.exists:
        report_crud_dir.mkdir()
    for file_name in report_crud_dir.listdir():
        if file_name.isfile() and file_name.basename.endswith(".yaml"):
            result.append(file_name.basename)
    return result


def crud_files_schedules():
    result = []
    if not schedules_crud_dir.exists:
        schedules_crud_dir.mkdir()
    for file_name in schedules_crud_dir.listdir():
        if file_name.isfile() and file_name.basename.endswith(".yaml"):
            result.append(file_name.basename)
    return result


@pytest.fixture(params=crud_files_reports())
def custom_report(request):
    with report_crud_dir.join(request.param).open(mode="r") as rep_yaml:
        return CustomReport(**yaml.load(rep_yaml))


@pytest.fixture(params=crud_files_schedules())
def schedule_data(request):
    with schedules_crud_dir.join(request.param).open(mode="r") as rep_yaml:
        return yaml.load(rep_yaml)


@pytest.mark.tier(3)
@test_requirements.report
def test_custom_report_crud(custom_report):
    custom_report.create()
    with update(custom_report):
        custom_report.title += fauxfactory.gen_alphanumeric()
    custom_report.queue(wait_for_finish=True)
    for report in custom_report.get_saved_reports():
        assert hasattr(report, 'data')
    custom_report.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1202412])
@test_requirements.report
def test_schedule_crud(schedule_data, appliance):
    schedules = ScheduleCollection(appliance)
    schedule = schedules.create(**schedule_data)
    with update(schedule):
        schedule.description = "badger badger badger"
    schedule.queue()
    schedule.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1388144, forced_streams=["5.7", "upstream"])])
def test_menuwidget_crud():
    w = MenuWidget(
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        shortcuts={
            "Services / Catalogs": fauxfactory.gen_alphanumeric(),
            "Cloud Intel / Dashboard": fauxfactory.gen_alphanumeric(),
        },
        visibility="<To All Users>"
    )
    w.create()
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1388144, forced_streams=["5.7", "upstream"])])
def test_reportwidget_crud():
    w = ReportWidget(
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        filter=["Events", "Operations", "Operations VMs Powered On/Off for Last Week"],
        columns=["VM Name", "Message"],
        rows="10",
        timer={"run": "Hourly", "hours": "Hour"},
        visibility="<To All Users>"
    )
    w.create()
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1388144, forced_streams=["5.7", "upstream"])])
def test_chartwidget_crud():
    w = ChartWidget(
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        filter="Configuration Management/Virtual Machines/Vendor and Guest OS",
        timer={"run": "Hourly", "hours": "Hour"},
        visibility="<To All Users>"
    )
    w.create()
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1388144, forced_streams=["5.7", "upstream"])])
def test_rssfeedwidget_crud():
    w = RSSFeedWidget(
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        type="Internal",
        feed="Administrative Events",
        rows="8",
        visibility="<To All Users>"
    )
    w.create()
    # Basic update
    with update(w):
        w.active = False
    # Different feed type
    with update(w):
        w.type = "External"
        w.external = "SlashDot"
    # and custom address
    with update(w):
        w.type = "External"
        w.external = "http://rss.example.com/"
    w.delete()


@pytest.mark.tier(3)
def test_dashboard_crud():
    d = Dashboard(
        fauxfactory.gen_alphanumeric(),
        "EvmGroup-administrator",
        title=fauxfactory.gen_alphanumeric(),
        locked=False,
        widgets=["Top CPU Consumers (weekly)", "Vendor and Guest OS Chart"]
    )
    d.create()
    with update(d):
        d.locked = True
    with update(d):
        d.locked = False
    with update(d):
        d.widgets = "Top Storage Consumers"
    d.delete()


@pytest.mark.tier(2)
@test_requirements.report
def test_run_report(appliance):
    report = appliance.rest_api.collections.reports.get(name='VM Disk Usage')
    response = report.action.run()
    assert appliance.rest_api.response.status_code == 200

    @wait_for_decorator(timeout="5m", delay=5)
    def rest_running_report_finishes():
        response.task.reload()
        if "error" in response.task.status.lower():
            pytest.fail("Error when running report: `{}`".format(response.task.message))
        return response.task.state.lower() == 'finished'

    result = appliance.rest_api.collections.results.get(id=response.result_id)
    assert result.name == report.name


@pytest.mark.tier(3)
@test_requirements.report
def test_import_report(appliance):
    menu_name = 'test_report_{}'.format(fauxfactory.gen_alphanumeric())
    data = {
        'report': {
            'menu_name': menu_name,
            'col_order': ['col1', 'col2', 'col3'],
            'cols': ['col1', 'col2', 'col3'],
            'rpt_type': 'Custom',
            'title': 'Test Report',
            'db': 'My::Db',
            'rpt_group': 'Custom',
        },
        'options': {'save': 'true'}
    }
    response, = appliance.rest_api.collections.reports.action.execute_action("import", data)
    assert appliance.rest_api.response.status_code == 200
    assert response['message'] == 'Imported Report: [{}]'.format(menu_name)
    report = appliance.rest_api.collections.reports.get(name=menu_name)
    assert report.name == menu_name

    response, = appliance.rest_api.collections.reports.action.execute_action("import", data)
    assert appliance.rest_api.response.status_code == 200
    assert response['message'] == 'Skipping Report (already in DB): [{}]'.format(menu_name)
