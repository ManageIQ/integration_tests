# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import yaml

from cfme import test_requirements
from cfme.intelligence.reports.schedules import ScheduleCollection
from cfme.intelligence.reports.widgets import AllDashboardWidgetsView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.path import data_path
from cfme.utils.rest import assert_response
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
def custom_report_values(request):
    with report_crud_dir.join(request.param).open(mode="r") as rep_yaml:
        return yaml.load(rep_yaml)


@pytest.fixture(params=crud_files_schedules())
def schedule_data(request):
    with schedules_crud_dir.join(request.param).open(mode="r") as rep_yaml:
        return yaml.load(rep_yaml)


@pytest.mark.sauce
@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1531600, forced_streams=["5.9"])])
@test_requirements.report
def test_custom_report_crud(custom_report_values, appliance):
    custom_report = appliance.collections.reports.create(**custom_report_values)
    with update(custom_report):
        custom_report.title += fauxfactory.gen_alphanumeric()
    custom_report.queue(wait_for_finish=True)
    for saved_report in custom_report.saved_reports.all():
        assert saved_report.exists
    custom_report.delete()


@pytest.mark.sauce
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


@pytest.mark.sauce
@pytest.mark.tier(3)
@test_requirements.report
def test_reports_disable_enable_schedule(schedule_data, appliance):
    schedules = appliance.collections.schedules
    schedule = schedules.create(**schedule_data)
    schedules.disable_schedules(schedule)
    assert not schedule.enabled
    schedules.enable_schedules(schedule)
    assert schedule.enabled
    schedule.delete()


@pytest.mark.sauce
@pytest.mark.tier(3)
def test_menuwidget_crud(appliance):
    w = appliance.collections.dashboard_report_widgets.create(
        appliance.collections.dashboard_report_widgets.MENU,
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        shortcuts={
            "Services / Catalogs": fauxfactory.gen_alphanumeric(),
            "Cloud Intel / Dashboard": fauxfactory.gen_alphanumeric(),
        },
        visibility="<To All Users>"
    )
    view = w.create_view(AllDashboardWidgetsView)
    view.flash.assert_message('Widget "{}" was saved'.format(w.title))
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.sauce
@pytest.mark.tier(3)
def test_reportwidget_crud(appliance):
    w = appliance.collections.dashboard_report_widgets.create(
        appliance.collections.dashboard_report_widgets.REPORT,
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        filter=["Events", "Operations", "Operations VMs Powered On/Off for Last Week"],
        columns=["VM Name", "Message"],
        rows="10",
        timer={"run": "Hourly", "hours": "Hour"},
        visibility="<To All Users>"
    )
    view = w.create_view(AllDashboardWidgetsView)
    view.flash.assert_message('Widget "{}" was saved'.format(w.title))
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.sauce
@pytest.mark.tier(3)
def test_chartwidget_crud(appliance):
    w = appliance.collections.dashboard_report_widgets.create(
        appliance.collections.dashboard_report_widgets.CHART,
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        filter="Configuration Management/Virtual Machines/Vendor and Guest OS",
        timer={"run": "Hourly", "hours": "Hour"},
        visibility="<To All Users>"
    )
    view = w.create_view(AllDashboardWidgetsView)
    view.flash.assert_message('Widget "{}" was saved'.format(w.title))
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.sauce
@pytest.mark.tier(3)
def test_rssfeedwidget_crud(appliance):
    w = appliance.collections.dashboard_report_widgets.create(
        appliance.collections.dashboard_report_widgets.RSS,
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        type="Internal",
        feed="Administrative Events",
        rows="8",
        visibility="<To All Users>"
    )
    view = w.create_view(AllDashboardWidgetsView)
    view.flash.assert_message('Widget "{}" was saved'.format(w.title))
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


@pytest.mark.sauce
@pytest.mark.tier(3)
def test_dashboard_crud(appliance):
    d = appliance.collections.report_dashboards.create(
        fauxfactory.gen_alphanumeric(),
        "EvmGroup-administrator",
        title=fauxfactory.gen_alphanumeric(),
        locked=False,
        widgets=["Top CPU Consumers (weekly)", "Vendor and Guest OS Chart"]
    )
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
    assert_response(appliance)

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
    assert_response(appliance)
    assert response['message'] == 'Imported Report: [{}]'.format(menu_name)
    report = appliance.rest_api.collections.reports.get(name=menu_name)
    assert report.name == menu_name

    response, = appliance.rest_api.collections.reports.action.execute_action("import", data)
    assert_response(appliance)
    assert response['message'] == 'Skipping Report (already in DB): [{}]'.format(menu_name)


@pytest.mark.sauce
@pytest.mark.tier(3)
@test_requirements.report
def test_reports_delete_saved_report(custom_report_values, appliance):
    """This test case deletes reports from the Saved Reports list.
    """
    report = appliance.collections.reports.create(**custom_report_values)
    report.queue(wait_for_finish=True)
    view = navigate_to(appliance.collections.saved_reports, 'All')
    # iterates through every row and checks if the 'Name' column matches the given value
    for row in view.table.rows():
        if row.read()['Name'] == report.title:
            row[0].check()
    view.configuration.item_select(
        item='Delete selected Saved Reports', handle_alert=True)
    report.delete()
