# -*- coding: utf-8 -*-
import pytest
import random

from cfme.intelligence.reports import menus, reports
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

# EvmGroup-super_administrator -> user `admin`
# If we add more, will need relogin + user creation
GROUPS = ["EvmGroup-super_administrator"]


def shuffle(l):
    """Simple deterministic shuffle.

    Ensures, that there is a change by moving all fields of iterable by 1.

    We need to ensure change to unlock Save button.
    """
    return [l[-1]] + l[:-1]


@pytest.yield_fixture(scope="function")
def report_menus(group):
    report_menus = menus.ReportMenu()
    yield report_menus
    report_menus.reset_to_default(group)


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1384518, forced_streams=["5.7", "upstream"])])
@pytest.mark.parametrize("group", GROUPS)
def test_shuffle_top_level(group, report_menus):
    # Shuffle the order
    with report_menus.manage_folder(group) as folder:
        order = shuffle(folder.fields)
        for item in reversed(order):
            folder.move_first(item)
    # Now go and read the tree
    view = navigate_to(reports.CustomReport, "All")
    table = [row["Name"].text for row in view.reports_table]
    if "My Company (All EVM Groups)" in table:
        del table[-1]
    assert table == order, "The order differs!"


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1384518, forced_streams=["5.7", "upstream"])])
@pytest.mark.parametrize("group", GROUPS)
def test_shuffle_first_level(group, report_menus):
    # Find a folder
    view = navigate_to(reports.CustomReport, "All")
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
    view = navigate_to(reports.CustomReport, "All")
    view.reports.tree.click_path("All Reports", selected_folder)
    table = [row["Name"].text for row in view.reports_table]
    assert table == order, "The order differs!"
