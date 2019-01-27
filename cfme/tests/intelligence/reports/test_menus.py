# -*- coding: utf-8 -*-
import random

import pytest
import yaml

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.rest.gen_data import users as _users
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.path import data_path

pytestmark = [pytest.mark.tier(3), test_requirements.report]

REPORT_CRUD_DIR = data_path.join("reports_crud")

# EvmGroup-super_administrator -> user `admin`
# If we add more, will need relogin + user creation
GROUPS = ["EvmGroup-super_administrator"]


def shuffle(l):
    """Simple deterministic shuffle.

    Ensures, that there is a change by moving all fields of iterable by 1.

    We need to ensure change to unlock Save button.
    """
    return [l[-1]] + l[:-1]


@pytest.fixture(scope="function")
def report_menus(group, appliance):
    report_menus = appliance.collections.intel_report_menus.instantiate()
    yield report_menus
    report_menus.reset_to_default(group)


def crud_files_reports():
    result = []
    if not REPORT_CRUD_DIR.exists:
        REPORT_CRUD_DIR.mkdir()
    for file_name in REPORT_CRUD_DIR.listdir():
        if file_name.isfile() and file_name.basename.endswith(".yaml"):
            result.append(file_name.basename)
    return result


@pytest.fixture(params=crud_files_reports())
def custom_report_values(request):
    with REPORT_CRUD_DIR.join(request.param).open(mode="r") as rep_yaml:
        return yaml.safe_load(rep_yaml)


@pytest.fixture(scope="function")
def get_custom_report(appliance, custom_report_values):
    custom_report = appliance.collections.reports.create(**custom_report_values)
    yield custom_report
    custom_report.delete()


@pytest.mark.parametrize("group", GROUPS)
def test_shuffle_top_level(appliance, group, report_menus):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/6h
    """
    # Shuffle the order
    with report_menus.manage_folder(group) as folder:
        order = shuffle(folder.fields)
        for item in reversed(order):
            folder.move_first(item)
    # Now go and read the tree
    view = navigate_to(appliance.collections.reports, "All")
    table = [row["Name"].text for row in view.reports_table]
    if view.mycompany_title in table:
        del table[-1]
    assert table == order, "The order differs!"


@pytest.mark.parametrize("group", GROUPS)
def test_shuffle_first_level(appliance, group, report_menus):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/3h
    """
    # Find a folder
    view = navigate_to(appliance.collections.reports, "All")
    tree = view.reports.tree.read_contents()[1]
    # Select some folder that has at least 3 children
    folders = map(
        lambda item: item[0],
        filter(lambda item: isinstance(item[1], list) and len(item[1]) >= 3, tree),
    )

    selected_folder = random.choice(folders)
    # Shuffle the order
    with report_menus.manage_folder(group, selected_folder) as folder:
        order = shuffle(folder.fields)
        for item in reversed(order):
            folder.move_first(item)
    # Now go and read the tree
    view = navigate_to(appliance.collections.reports, "All")
    view.reports.tree.click_path("All Reports", selected_folder)
    table = [row["Name"].text for row in view.reports_table]
    assert table == order, "The order differs!"


@pytest.mark.parametrize("group", GROUPS)
def test_add_reports_to_available_reports_menu(
    appliance, request, group, report_menus, get_custom_report
):
    """This test case moves custom report to existing menus

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/10h
    """
    folder = random.choice(report_menus.get_folders(group))
    sub_folder = random.choice(report_menus.get_subfolders(group, folder))
    report_menus.move_reports(group, folder, sub_folder, get_custom_report.menu_name)
    report = appliance.collections.reports.instantiate(
        type=folder, subtype=sub_folder, menu_name=get_custom_report.menu_name
    )
    assert report.exists


@pytest.fixture()
def rbac_user(appliance, request, group):
    user, user_data = _users(request, appliance, group=group)
    yield appliance.collections.users.instantiate(
        name=user[0].name,
        credential=Credential(
            principal=user_data[0]["userid"], secret=user_data[0]["password"]
        ),
        groups=[group],
    )

    if user[0].exists:
        user[0].action.delete()


@pytest.mark.tier(1)
@pytest.mark.parametrize("group", ["EvmGroup-administrator"])
def test_rbac_move_custom_report(
    appliance, request, group, get_custom_report, report_menus, rbac_user
):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/5h
        startsin: 5.10
        testSteps:
            1. Create a custom report, select a group and move the report to a certain menu.
            2. Create a user belonging to the previously selected group.
            3. Login with the user and check if the report is available under that menu.

    Bugzilla:
        1670293
    """
    folder, subfolder = "Tenants", "Tenant Quotas"
    report_menus.move_reports(group, folder, subfolder, get_custom_report.menu_name)
    with rbac_user:
        rbac_report = appliance.collections.reports.instantiate(
            type=folder, subtype=subfolder, menu_name=get_custom_report.menu_name
        )
        assert rbac_report.exists


@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[BZ(1676638, forced_streams=["5.9", "5.10"])])
@pytest.mark.parametrize("group", GROUPS)
def test_reports_menu_with_duplicate_reports(
    appliance, request, group, report_menus, custom_report_values
):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/10h
        startsin: 5.9
        setup:
            1.Create a custom report or copy an existing report.
            2. Move the custom report to 'Tenants > Tenant Quotas' menu in user's current group
        testSteps:
            1. See if the report is available under 'Tenants > Tenant Quotas'.
            2. Delete the custom report.
            3. See if the report is available under 'Tenants > Tenant Quotas'.
            4. Add a new report with the same menu_name.
            5. See if the report is available under 'Tenants > Tenant Quotas'.
        expectedResults:
            1. Report must be visible.
            2.
            3. Report must not be visible.
            4.
            5. Report must not be visible.
    """
    custom_report_1 = appliance.collections.reports.create(**custom_report_values)
    folder, subfolder = "Tenants", "Tenant Quotas"
    report_menus.move_reports(group, folder, subfolder, custom_report_1.menu_name)
    report = appliance.collections.reports.instantiate(
        type=folder, subtype=subfolder, menu_name=custom_report_1.menu_name
    )
    assert report.exists
    custom_report_1.delete()
    assert not report.exists
    custom_report_2 = appliance.collections.reports.create(**custom_report_values)
    request.addfinalizer(custom_report_2.delete)
    assert not report.exists