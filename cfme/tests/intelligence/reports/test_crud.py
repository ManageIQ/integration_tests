import datetime

import fauxfactory
import pytest
import yaml

from cfme import test_requirements
from cfme.intelligence.reports.schedules import ScheduleDetailsView
from cfme.intelligence.reports.widgets import AllDashboardWidgetsView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.path import data_path
from cfme.utils.rest import assert_response
from cfme.utils.update import update
from cfme.utils.wait import wait_for_decorator

pytestmark = [test_requirements.report]

REPORT_CRUD_DIR = data_path.join("reports_crud")
SCHEDULES_CRUD_DIR = data_path.join("schedules_crud")


def crud_files_reports():
    result = []
    if not REPORT_CRUD_DIR.exists:
        REPORT_CRUD_DIR.mkdir()
    for file_name in REPORT_CRUD_DIR.listdir():
        if file_name.isfile() and file_name.basename.endswith(".yaml"):
            result.append(file_name.basename)
    return result


def crud_files_schedules():
    result = []
    if not SCHEDULES_CRUD_DIR.exists:
        SCHEDULES_CRUD_DIR.mkdir()
    for file_name in SCHEDULES_CRUD_DIR.listdir():
        if file_name.isfile() and file_name.basename.endswith(".yaml"):
            result.append(file_name.basename)
    return result


@pytest.fixture(params=crud_files_reports())
def custom_report_values(request):
    with REPORT_CRUD_DIR.join(request.param).open(mode="r") as rep_yaml:
        return yaml.safe_load(rep_yaml)


@pytest.fixture(params=crud_files_schedules())
def schedule_data(request):
    with SCHEDULES_CRUD_DIR.join(request.param).open(mode="r") as rep_yaml:
        return yaml.safe_load(rep_yaml)


@pytest.fixture(scope="function")
def get_custom_report(appliance, custom_report_values):
    custom_report = appliance.collections.reports.create(**custom_report_values)
    yield custom_report
    custom_report.delete()


@pytest.mark.rhel_testing
@pytest.mark.sauce
@pytest.mark.tier(3)
def test_custom_report_crud(custom_report_values, appliance, request):
    """
    Bugzilla:
        1531600

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: critical
        initialEstimate: 1/16h
    """
    custom_report = appliance.collections.reports.create(**custom_report_values)
    request.addfinalizer(custom_report.delete_if_exists)

    with update(custom_report):
        custom_report.title += fauxfactory.gen_alphanumeric()
    custom_report.queue(wait_for_finish=True)
    for saved_report in custom_report.saved_reports.all():
        assert saved_report.exists
    custom_report.delete()


@pytest.mark.sauce
@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1729882, 1202412, 1446052])
def test_reports_schedule_crud(schedule_data, appliance, request):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/16h

    Bugzilla:
        1202412
        1446052
        1729882
    """
    # create
    schedule = appliance.collections.schedules.create(**schedule_data)
    request.addfinalizer(schedule.delete_if_exists)

    view = schedule.create_view(ScheduleDetailsView)
    view.flash.assert_success_message(f'Schedule "{schedule.name}" was added')

    # update
    date = datetime.datetime.today() + datetime.timedelta(5)
    updated_description = "badger badger badger"
    updated_timer = {"run": "Monthly", "starting_date": date}

    with update(schedule):
        schedule.description = updated_description
        schedule.timer = updated_timer
    view.flash.assert_message(f'Schedule "{schedule.name}" was saved')

    assert view.schedule_info.get_text_of("Description") == updated_description

    run_at = view.schedule_info.get_text_of("Run At")
    assert updated_timer["run"].lower() in run_at
    assert str(date.day) in run_at

    # queue
    schedule.queue()
    view.flash.assert_message("The selected Schedule has been queued to run")

    # delete
    schedule.delete()
    view.flash.assert_message(f"Schedule {schedule.name} was deleted")


# Currently, the BZ 1667064 is reported only against 5.10, but is present in
# 5.11 as well. It is DEFERED.
@pytest.mark.sauce
@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1667064])
def test_menuwidget_crud(appliance, request):
    """
    Bugzilla:
        1653796
        1667064

    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        caseimportance: critical
        initialEstimate: 1/12h
    """
    w = appliance.collections.dashboard_report_widgets.create(
        appliance.collections.dashboard_report_widgets.MENU,
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        shortcuts={
            "Services / Catalogs": fauxfactory.gen_alphanumeric(),
            "Overview / Dashboard": fauxfactory.gen_alphanumeric(),
        },
        visibility="<To All Users>"
    )
    request.addfinalizer(w.delete_if_exists)

    view = w.create_view(AllDashboardWidgetsView)
    view.flash.assert_message(f'Widget "{w.title}" was saved')
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.sauce
@pytest.mark.tier(3)
def test_reportwidget_crud(appliance, request):
    """
    Bugzilla:
        1656413

    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        initialEstimate: 1/12h
        caseimportance: critical
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
        visibility="<To All Users>"
    )
    request.addfinalizer(w.delete_if_exists)

    view = w.create_view(AllDashboardWidgetsView)
    view.flash.assert_message(f'Widget "{w.title}" was saved')
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.sauce
@pytest.mark.tier(3)
def test_chartwidget_crud(appliance, request):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        caseimportance: critical
        initialEstimate: 1/12h
    """
    w = appliance.collections.dashboard_report_widgets.create(
        appliance.collections.dashboard_report_widgets.CHART,
        fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        active=True,
        filter="Configuration Management/Virtual Machines/Vendor and Guest OS",
        timer={"run": "Hourly", "hours": "Hour"},
        visibility="<To All Users>"
    )
    request.addfinalizer(w.delete_if_exists)

    view = w.create_view(AllDashboardWidgetsView)
    view.flash.assert_message(f'Widget "{w.title}" was saved')
    with update(w):
        w.active = False
    w.delete()


@pytest.mark.sauce
@pytest.mark.tier(3)
@pytest.mark.ignore_stream("5.11", "upstream")  # BZ 1728328
def test_rssfeedwidget_crud(appliance, request):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        caseimportance: critical
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
        visibility="<To All Users>"
    )
    request.addfinalizer(w.delete_if_exists)

    view = w.create_view(AllDashboardWidgetsView)
    view.flash.assert_message(f'Widget "{w.title}" was saved')
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
@pytest.mark.sauce
@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1667064])
def test_dashboard_crud(appliance, request):
    """
    Polarion:
        assignee: jhenner
        caseimportance: critical
        casecomponent: Reporting
        initialEstimate: 1/12h

    Bugzilla:
        1667064
    """
    d = appliance.collections.report_dashboards.create(
        fauxfactory.gen_alphanumeric(),
        "EvmGroup-administrator",
        title=fauxfactory.gen_alphanumeric(),
        locked=False,
        widgets=["Top CPU Consumers (weekly)", "Vendor and Guest OS Chart"]
    )
    request.addfinalizer(d.delete_if_exists)

    with update(d):
        d.locked = True
    with update(d):
        d.locked = False
    with update(d):
        d.widgets = "Top Storage Consumers"
    d.delete()


@pytest.mark.tier(2)
def test_run_report(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/16h
    """
    report = appliance.rest_api.collections.reports.get(name='VM Disk Usage')
    response = report.action.run()
    assert_response(appliance)

    @wait_for_decorator(timeout="5m", delay=5)
    def rest_running_report_finishes():
        response.task.reload()
        if "error" in response.task.status.lower():
            pytest.fail(f"Error when running report: `{response.task.message}`")
        return response.task.state.lower() == 'finished'

    result = appliance.rest_api.collections.results.get(id=response.result_id)
    assert result.name == report.name


@pytest.mark.tier(3)
def test_import_report_rest(appliance, request):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/16h
    """
    menu_name = fauxfactory.gen_alphanumeric(18, start="test_report_")
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

    @request.addfinalizer
    def _finalize():
        report = appliance.collections.reports.instantiate(
            type="My Company (All Groups)", subtype="Custom", menu_name=menu_name
        )
        report.delete_if_exists()

    assert response['message'] == f'Imported Report: [{menu_name}]'
    report = appliance.rest_api.collections.reports.get(name=menu_name)
    assert report.name == menu_name

    response, = appliance.rest_api.collections.reports.action.execute_action("import", data)
    assert_response(appliance)
    assert response['message'] == f'Skipping Report (already in DB): [{menu_name}]'


@pytest.mark.sauce
@pytest.mark.tier(3)
def test_reports_delete_saved_report(appliance, request):
    """The test case selects reports from the Saved Reports list and deletes them.

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/16h
    """
    report = appliance.collections.reports.instantiate(
        type="Configuration Management",
        subtype="Virtual Machines",
        menu_name="Hardware Information for VMs",
    ).queue(wait_for_finish=True)
    request.addfinalizer(report.delete_if_exists)

    view = navigate_to(appliance.collections.saved_reports, 'All')
    # iterates through every row and checks if the 'Name' column matches the given value
    for row in view.table.rows():
        if row.name.text == report.report.menu_name:
            row[0].check()
    view.configuration.item_select(
        item='Delete selected Saved Reports', handle_alert=True)
    assert not report.exists


@pytest.mark.tier(1)
def test_reports_crud_schedule_for_base_report_once(appliance, request):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/16h
    """
    report = appliance.collections.reports.instantiate(
        type="Configuration Management",
        subtype="Virtual Machines",
        menu_name="Hardware Information for VMs",
    )
    data = {
        "timer": {"hour": "12", "minute": "10"},
        "email": {
            "to_emails": "test@example.com"
        },
        "email_options": {
            "send_if_empty": True,
            "send_pdf": True,
            "send_csv": True,
            "send_txt": True,
        },
    }
    schedule = report.create_schedule(**data)
    request.addfinalizer(schedule.delete_if_exists)

    assert schedule.enabled
    schedule.delete(cancel=False)
    assert not schedule.exists


def test_crud_custom_report_schedule(appliance, request, get_custom_report, schedule_data):
    """This test case creates a schedule for custom reports and tests if it was created
    successfully.

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/10h
    """
    schedule_data["report_filter"] = {
        "filter_type": "My Company (All Groups)",
        "subfilter_type": "Custom",
        "report_type": get_custom_report.menu_name,
    }
    custom_report_schedule = appliance.collections.schedules.create(**schedule_data)
    request.addfinalizer(custom_report_schedule.delete_if_exists)

    assert custom_report_schedule.exists
    custom_report_schedule.delete(cancel=False)
