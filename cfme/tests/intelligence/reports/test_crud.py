# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import yaml

from cfme.fixtures import pytest_selenium as sel
from cfme.intelligence.reports.dashboards import Dashboard
from cfme.intelligence.reports.reports import CustomReport
from cfme.intelligence.reports.schedules import Schedule
from cfme.intelligence.reports.widgets import ChartWidget, MenuWidget, ReportWidget, RSSFeedWidget
from utils.path import data_path
from utils.update import update
from utils import version


report_crud_dir = data_path.join("reports_crud")
schedules_crud_dir = data_path.join("schedules_crud")


def crud_files_reports():
    result = []
    if not report_crud_dir.exists():
        report_crud_dir.mkdir()
    for file in report_crud_dir.listdir():
        if file.isfile() and file.basename.endswith(".yaml"):
            result.append(file.basename)
    return result


def crud_files_schedules():
    result = []
    if not schedules_crud_dir.exists():
        schedules_crud_dir.mkdir()
    for file in schedules_crud_dir.listdir():
        if file.isfile() and file.basename.endswith(".yaml"):
            result.append(file.basename)
    return result


@pytest.fixture(params=crud_files_reports())
def custom_report(request):
    with report_crud_dir.join(request.param).open(mode="r") as rep_yaml:
        return CustomReport(**yaml.load(rep_yaml))


@pytest.fixture(params=crud_files_schedules())
def schedule(request):
    with schedules_crud_dir.join(request.param).open(mode="r") as rep_yaml:
        data = yaml.load(rep_yaml)
        name = data.pop("name")
        description = data.pop("description")
        filter = data.pop("filter")
        return Schedule(name, description, filter, **data)


@pytest.mark.tier(3)
def test_custom_report_crud(custom_report):
    custom_report.create()
    with update(custom_report):
        custom_report.title += fauxfactory.gen_alphanumeric()
    custom_report.queue(wait_for_finish=True)
    for report in custom_report.get_saved_reports():
        report.data  # touch the results
    custom_report.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1202412])
def test_schedule_crud(schedule):
    schedule.create()
    with update(schedule):
        schedule.description = "badger badger badger"
    schedule.queue(wait_for_finish=True)
    schedule.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1209945])
def test_menuwidget_crud():
    w = MenuWidget(
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        shortcuts={
            "Services / Catalogs": fauxfactory.gen_alphanumeric(),
            "Clouds / Providers": fauxfactory.gen_alphanumeric(),
        },
        visibility=["<By Role>", sel.ByText("EvmRole-administrator")]
    )
    w.create()
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1209945])
def test_reportwidget_crud():
    w = ReportWidget(
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        filter=["Events", "Operations", "Operations VMs Powered On/Off for Last Week"],
        columns=["VM Name", "Message"],
        rows="10",
        timer={"run": "Hourly", "hours": "Hour"},
        visibility=["<By Role>", sel.ByText("EvmRole-administrator")]
    )
    w.create()
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1209945])
def test_chartwidget_crud():
    w = ChartWidget(
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        filter="Configuration Management/Virtual Machines/Vendor and Guest OS",
        timer={"run": "Hourly", "hours": "Hour"},
        visibility=["<By Role>", sel.ByText("EvmRole-administrator")]
    )
    w.create()
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1209945])
def test_rssfeedwidget_crud():
    w = RSSFeedWidget(
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        type="Internal",
        feed="Administrative Events",
        rows="8",
        visibility=["<By Role>", sel.ByText("EvmRole-administrator")]
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
        fauxfactory.gen_alphanumeric(),
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
@pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
def test_run_report(rest_api):
    report = rest_api.collections.reports.get(name='VM Disk Usage')
    response = report.action.run()

    @pytest.wait_for(timeout="5m", delay=5)
    def rest_running_report_finishes():
        response.task.reload()
        if response.task.status.lower() in {"error"}:
            pytest.fail("Error when running report: `{}`".format(response.task.message))
        return response.task.state.lower() == 'finished'

    result = rest_api.collections.results.get(id=response.result_id)
    assert result.name == report.name


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
def test_import_report(rest_api):
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
    response, = rest_api.collections.reports.action.execute_action("import", data)
    assert response['message'] == 'Imported Report: [{}]'.format(menu_name)
    report = rest_api.collections.reports.get(name=menu_name)
    assert report.name == menu_name

    response, = rest_api.collections.reports.action.execute_action("import", data)
    assert response['message'] == 'Skipping Report (already in DB): [{}]'.format(menu_name)
