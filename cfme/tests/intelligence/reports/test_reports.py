import fauxfactory
import pytest

from cfme import test_requirements
from cfme.rest.gen_data import users as _users
from cfme.utils.rest import assert_response

pytestmark = [test_requirements.report, pytest.mark.tier(3), pytest.mark.sauce]


@pytest.fixture
def create_custom_tag(appliance):
    # cannot create a category with uppercase in the name
    category_name = fauxfactory.gen_alphanumeric().lower()
    category = appliance.rest_api.collections.categories.action.create(
        {
            "name": "{cat_name}".format(cat_name=category_name),
            "description": "description_{cat_name}".format(cat_name=category_name),
        }
    )[0]
    assert_response(appliance)

    tag = appliance.rest_api.collections.tags.action.create(
        {
            "name": "{cat_name}_entry".format(cat_name=category_name),
            "description": "{cat_name}_entry_description".format(cat_name=category_name),
            "category": {"href": category.href},
        }
    )[0]
    assert_response(appliance)

    yield category_name

    tag.action.delete()
    category.action.delete()


@pytest.fixture(scope="function")
def rbac_api(appliance, request):
    user, user_data = _users(
        request, appliance, password="smartvm", group="EvmGroup-user"
    )
    api = appliance.new_rest_api_instance(
        entry_point=appliance.rest_api._entry_point,
        auth=(user[0].userid, user_data[0]["password"]),
    )
    assert_response(api)
    yield api
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
    assert_response(appliance)
    assert len(report_data)


@pytest.mark.tier(1)
def test_reports_custom_tags(appliance, request, create_custom_tag):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: low
        initialEstimate: 1/3h
        setup:
            1. Add custom tags to appliance using black console
                i. ssh to appliance, vmdb; rails c
                ii. cat = Classification.create_category!(
                    name: "rocat1", description: "read_only cat 1", read_only: true)
                iii. cat.add_entry(name: "roent1", description: "read_only entry 1")
        testSteps:
            1. Create a new report with the newly created custom tag/category.
        expectedResults:
            1. Report must be created successfully.
    """
    category_name = create_custom_tag
    report_data = {
        "menu_name": "Custom Category Report {}".format(category_name),
        "title": "Custom Category Report Title {}".format(category_name),
        "base_report_on": "Availability Zones",
        "report_fields": [
            "Cloud Manager.My Company Tags : description_{}".format(category_name),
            "VMs.My Company Tags : description_{}".format(category_name),
        ],
    }
    report = appliance.collections.reports.create(**report_data)
    request.addfinalizer(report.delete)
    assert report.exists
