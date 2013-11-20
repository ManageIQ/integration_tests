"""Navigation fixtures for use in tests."""
# -*- coding: utf8 -*-
import pytest
from itertools import dropwhile
from copy import deepcopy
import pages.regions.header_menu as menu


nav_tree = menu.menu_tree

_width_errmsg = '''The minimum supported width of CFME is 1280 pixels

Some navigation fixtures will fail if the browser window is too small
due to submenu elements being rendered off the screen.
'''


@pytest.fixture
def home_page_logged_in(selenium):
    """Log in to the appliance and return the home page."""
    # window_size = selenium.get_window_size()
    # Assert.greater_equal(window_size['width'], 1280, _width_errmsg)
    from pages.login import login_admin
    login_admin()
    # Assert.true(home_pg.is_logged_in, 'Could not determine if logged in')


def tree_path(target, tree):
    if tree[0] == target:
        return []
    elif len(tree) > 2:
        for idx, child in enumerate(tree[2]):
            found = tree_path(target, child)
            if not (found is None):
                return [idx] + found
                return None


def tree_find(tree, path=[]):
    node = [[tree[0], tree[1]]]
    if path:
        return node + tree_find(tree[2][path[0]], path[1:])
    else:
        return node


def tree_graft(tree, branches, target):
    path = tree_path(target, tree)
    new_tree = deepcopy(tree)
    node = new_tree
    for idx in path:
        node = node[2][idx]
        for branch in branches:
            if len(node) > 2:
                node[2].append(branch)
            else:
                node.append([branch])
                return new_tree


def navigate(tree, end, start=None):
    steps = tree_find(tree, tree_path(end, tree))
    print(steps)
    if steps is None:
        raise ValueError("Destination not found in navigation tree: %s" % end)
    if start:
        steps = dropwhile(lambda s: s[0] != start, steps)
        if len(steps) == 0:
            raise ValueError("Starting location %s not found in navigation tree." % start)
    for step in steps:
        step[1]()


def go_to(dest, start=None):
    navigate(nav_tree, dest, start)
