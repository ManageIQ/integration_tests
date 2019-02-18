# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import yaml

from cfme import test_requirements
from cfme.intelligence.reports.widgets import AllDashboardWidgetsView
from cfme.utils.blockers import BZ
from cfme.utils.path import data_path
from cfme.utils.update import update

pytestmark = [test_requirements.report, pytest.mark.tier(3), pytest.mark.sauce]

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
        return yaml.safe_load(rep_yaml)


@pytest.fixture(params=crud_files_schedules())
def schedule_data(request):
    with schedules_crud_dir.join(request.param).open(mode="r") as rep_yaml:
        return yaml.safe_load(rep_yaml)


@pytest.fixture(scope="function")
def get_custom_report(appliance, custom_report_values):
    custom_report = appliance.collections.reports.create(**custom_report_values)
    yield custom_report
    custom_report.delete()


@pytest.mark.rhel_testing
@pytest.mark.meta(blockers=[BZ(1531600, forced_streams=["5.9"])])
def test_custom_report_crud(custom_report_values, appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/16h
        tags: report
    """
    custom_report = appliance.collections.reports.create(**custom_report_values)
    with update(custom_report):
        custom_report.title += fauxfactory.gen_alphanumeric()
    custom_report.queue(wait_for_finish=True)
    for saved_report in custom_report.saved_reports.all():
        assert saved_report.exists
    custom_report.delete()


@pytest.mark.meta(blockers=[1202412])
def test_schedule_crud(schedule_data, appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/16h
        tags: report
    """
    schedule = appliance.collections.schedules.create(**schedule_data)
    with update(schedule):
        schedule.description = "badger badger badger"
    schedule.queue()
    schedule.delete()


@pytest.mark.meta(blockers=[BZ(1653796), BZ(1667064)])
def test_menuwidget_crud(appliance):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    w = appliance.collections.dashboard_report_widgets.create(
        appliance.collections.dashboard_report_widgets.MENU,
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        shortcuts={
            "Services / Catalogs": fauxfactory.gen_alphanumeric(),
            "Cloud Intel / Dashboard": fauxfactory.gen_alphanumeric(),
        },
        visibility="<To All Users>",
    )
    view = w.create_view(AllDashboardWidgetsView)
    view.flash.assert_message('Widget "{}" was saved'.format(w.title))
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.meta(blockers=[BZ(1656413), BZ(1667064)])
def test_reportwidget_crud(appliance):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    w = appliance.collections.dashboard_report_widgets.create(
        appliance.collections.dashboard_report_widgets.REPORT,
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        filter=["Events", "Operations", "Operations VMs Powered On/Off for Last Week"],
        columns=["VM Name", "Message"],
        rows="10",
        timer={"run": "Hourly", "hours": "Hour"},
        visibility="<To All Users>",
    )
    view = w.create_view(AllDashboardWidgetsView)
    view.flash.assert_message('Widget "{}" was saved'.format(w.title))
    if not BZ(1653796, forced_streams=["5.9"]).blocks:
        with update(w):
            w.active = False
    w.delete()


@pytest.mark.meta(blockers=[BZ(1653796), BZ(1667064)])
def test_chartwidget_crud(appliance):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    w = appliance.collections.dashboard_report_widgets.create(
        appliance.collections.dashboard_report_widgets.CHART,
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        filter="Configuration Management/Virtual Machines/Vendor and Guest OS",
        timer={"run": "Hourly", "hours": "Hour"},
        visibility="<To All Users>",
    )
    view = w.create_view(AllDashboardWidgetsView)
    view.flash.assert_message('Widget "{}" was saved'.format(w.title))
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.meta(blockers=[BZ(1653796), BZ(1667064)])
def test_rssfeedwidget_crud(appliance):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    w = appliance.collections.dashboard_report_widgets.create(
        appliance.collections.dashboard_report_widgets.RSS,
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        type="Internal",
        feed="Administrative Events",
        rows="8",
        visibility="<To All Users>",
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


@pytest.mark.rhel_testing
@pytest.mark.meta(blockers=[BZ(1667064)])
def test_dashboard_crud(appliance):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    d = appliance.collections.report_dashboards.create(
        fauxfactory.gen_alphanumeric(),
        "EvmGroup-administrator",
        title=fauxfactory.gen_alphanumeric(),
        locked=False,
        widgets=["Top CPU Consumers (weekly)", "Vendor and Guest OS Chart"],
    )
    with update(d):
        d.locked = True
    with update(d):
        d.locked = False
    with update(d):
        d.widgets = "Top Storage Consumers"
    d.delete()


@pytest.mark.tier(1)
def test_reports_crud_schedule_for_base_report_once(appliance, request):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/16h
        tags: report
    """
    report = appliance.collections.reports.instantiate(
        type="Configuration Management",
        subtype="Virtual Machines",
        menu_name="Hardware Information for VMs",
    )
    data = {
        "timer": {"hour": "12", "minute": "10"},
        "emails": "test@example.com",
        "email_options": {
            "send_if_empty": True,
            "send_pdf": True,
            "send_csv": True,
            "send_txt": True,
        },
    }
    schedule = report.create_schedule(**data)

    assert schedule.enabled
    schedule.delete(cancel=False)
    assert not schedule.exists


def test_crud_custom_report_schedule(
    appliance, request, get_custom_report, schedule_data
):
    """This test case creates a schedule for custom reports and tests if it was created
    successfully.

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/10h
        tags: report
    """
    schedule_data["filter"] = (
        "My Company (All Groups)",
        "Custom",
        get_custom_report.menu_name,
    )
    custom_report_schedule = appliance.collections.schedules.create(**schedule_data)
    assert custom_report_schedule.exists
    custom_report_schedule.delete(cancel=False)
