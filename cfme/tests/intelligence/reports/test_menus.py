# -*- coding: utf-8 -*-
import pytest
import random
import yaml

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.path import data_path


report_crud_dir = data_path.join("reports_crud")

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
    if not report_crud_dir.exists:
        report_crud_dir.mkdir()
    for file_name in report_crud_dir.listdir():
        if file_name.isfile() and file_name.basename.endswith(".yaml"):
            result.append(file_name.basename)
    return result


@pytest.fixture(params=crud_files_reports())
def custom_report_values(request):
    with report_crud_dir.join(request.param).open(mode="r") as rep_yaml:
        return yaml.load(rep_yaml)


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1541324, forced_streams=["5.9"])])
@pytest.mark.parametrize("group", GROUPS)
def test_shuffle_top_level(appliance, group, report_menus):
    """
    Polarion:
        assignee: pvala
        casecomponent: report
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


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1541324, forced_streams=["5.9"])])
@pytest.mark.parametrize("group", GROUPS)
def test_shuffle_first_level(appliance, group, report_menus):
    """
    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/3h
    """
    # Find a folder
    view = navigate_to(appliance.collections.reports, "All")
    tree = view.reports.tree.read_contents()[1]
    # Select some folder that has at least 3 children
    folders = map(lambda item: item[0],
                  filter(lambda item: isinstance(item[1], list) and len(item[1]) >= 3, tree))

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


@pytest.mark.tier(3)
@pytest.mark.parametrize("group", GROUPS)
@test_requirements.report
def test_add_reports_to_available_reports_menu(appliance, request, group,
                                               report_menus, custom_report_values):
    """This test case moves custom menu to existing menus

    Polarion:
        assignee: pvala
        casecomponent: report
        initialEstimate: None
    """

    custom_report = appliance.collections.reports.create(**custom_report_values)
    request.addfinalizer(custom_report.delete)
    folder = random.choice(report_menus.get_folders(group))
    sub_folder = random.choice(report_menus.get_subfolders(group, folder))
    with report_menus.manage_subfolder(group, folder, sub_folder) as selected:
        selected.available_options.fill(custom_report.menu_name)
        selected.move_into_button.click()
    report = appliance.collections.reports.instantiate(
        type=folder, subtype=sub_folder, menu_name=custom_report.menu_name)
    assert report.exists
