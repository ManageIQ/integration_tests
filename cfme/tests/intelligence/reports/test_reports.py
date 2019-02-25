import fauxfactory
import pytest

from cfme import test_requirements
from cfme.rest.gen_data import users as _users
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.rest import assert_response
from cfme.utils.wait import wait_for_decorator

pytestmark = [test_requirements.report, pytest.mark.tier(3), pytest.mark.sauce]


@pytest.fixture(scope="function")
def rbac_api(appliance, request):
    user, user_data = _users(
        request, appliance, password="smartvm", group="EvmGroup-user"
    )
    yield appliance.new_rest_api_instance(
        entry_point=appliance.rest_api._entry_point,
        auth=(user[0].userid, user_data[0]["password"]),
    )
    appliance.rest_api.collections.users.action.delete(id=user[0].id)


@test_requirements.rest
@pytest.mark.tier(1)
def test_non_admin_user_reports_access_rest(appliance, request, rbac_api):
    """ This test checks if a non-admin user with proper privileges can access all reports via API.

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/12h
        tags: report
        setup:
            1. Create a user with privilege to access reports and REST.
            2. Instantiate a MiqApi instance with the user.
        testSteps:
            1. Access all reports with the new user with the help of newly instantiated API.
        expectedResults:
            1. User should be able to access all reports.
    """
    report_data = rbac_api.collections.reports.all
    assert_response(rbac_api)
    assert len(report_data)


def test_reports_delete_saved_report(appliance, request):
    """The test case selects reports from the Saved Reports list and deletes them.

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
    ).queue(wait_for_finish=True)
    request.addfinalizer(report.delete_if_exists)
    view = navigate_to(appliance.collections.saved_reports, "All")
    # iterates through every row and checks if the 'Name' column matches the given value
    for row in view.table.rows():
        if row.name.text == report.report.menu_name:
            row[0].check()
    view.configuration.item_select(
        item="Delete selected Saved Reports", handle_alert=True
    )
    assert not report.exists


def test_import_report(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/16h
        tags: report
    """
    menu_name = "test_report_{}".format(fauxfactory.gen_alphanumeric())
    data = {
        "report": {
            "menu_name": menu_name,
            "col_order": ["col1", "col2", "col3"],
            "cols": ["col1", "col2", "col3"],
            "rpt_type": "Custom",
            "title": "Test Report",
            "db": "My::Db",
            "rpt_group": "Custom",
        },
        "options": {"save": "true"},
    }
    response, = appliance.rest_api.collections.reports.action.execute_action(
        "import", data
    )
    assert_response(appliance)
    assert response["message"] == "Imported Report: [{}]".format(menu_name)
    report = appliance.rest_api.collections.reports.get(name=menu_name)
    assert report.name == menu_name

    response, = appliance.rest_api.collections.reports.action.execute_action(
        "import", data
    )
    assert_response(appliance)
    assert response["message"] == "Skipping Report (already in DB): [{}]".format(
        menu_name
    )


@pytest.mark.tier(2)
def test_run_report(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/16h
        tags: report
    """
    report = appliance.rest_api.collections.reports.get(name="VM Disk Usage")
    response = report.action.run()
    assert_response(appliance)

    @wait_for_decorator(timeout="5m", delay=5)
    def rest_running_report_finishes():
        response.task.reload()
        if "error" in response.task.status.lower():
            pytest.fail("Error when running report: `{}`".format(response.task.message))
        return response.task.state.lower() == "finished"

    result = appliance.rest_api.collections.results.get(id=response.result_id)
    assert result.name == report.name
