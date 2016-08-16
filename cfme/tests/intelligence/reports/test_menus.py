# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pytest
import random

from cfme.intelligence.reports import menus
from cfme.web_ui import Tree, accordion

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
def on_finish_default(group):
    yield
    menus.reset_to_default(group)


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1101250, 1132118])
@pytest.mark.parametrize("group", GROUPS)
def test_shuffle_top_level(group, on_finish_default):
    # Shuffle the order
    with menus.manage_folder(group) as folder:
        order = shuffle(folder.fields)
        for item in reversed(order):
            folder.move_first(item)
    # Now go and read the tree
    pytest.sel.force_navigate("reports")
    tree = accordion.tree("Reports").read_contents()
    checked = Tree.flatten_level(Tree.browse(tree, "All Reports"))
    assert checked == order, "The order differs!"


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1101250, 1132118])
@pytest.mark.parametrize("group", GROUPS)
def test_shuffle_first_level(group, on_finish_default):
    # Find a folder
    pytest.sel.force_navigate("reports")
    tree = accordion.tree("Reports").read_contents()
    folders = Tree.browse(tree, "All Reports")
    # Select some folder that has at least 3 children
    folders = map(lambda item: item[0],
                filter(lambda item: isinstance(item[1], list) and len(item[1]) >= 3, folders))
    selected_folder = random.choice(folders)
    # Shuffle the order
    with menus.manage_folder(group, selected_folder) as folder:
        order = shuffle(folder.fields)
        for item in reversed(order):
            folder.move_first(item)
    # Now go and read the tree
    pytest.sel.force_navigate("reports")
    tree = accordion.tree("Reports").read_contents()
    checked = Tree.flatten_level(Tree.browse(tree, "All Reports", selected_folder))
    assert checked == order, "The order differs!"
