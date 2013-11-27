"""Navigation fixtures for use in tests."""
# -*- coding: utf8 -*-
import pytest
from itertools import dropwhile
from copy import deepcopy
from fixtures.pytest_selenium import move_to_element, click

if not 'nav_tree' in globals():
    nav_tree = ['toplevel', lambda: None]  # navigation tree with just a root node

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


# a navigation node is a tuple/list, first item a string name of the node,
# 2nd item either a function to navigate with, or a tuple/list of a function
# and a dict containing other nodes.

def _has_children(node):
    return (isinstance(node[1], (list, tuple)) and len(node[1]) > 1)


def _children(node):
    if _has_children(node):
        return node[1][1]
    else:
        return {}


def _get_child(node, name):
    return [name, _children(node).get(name)]


def _name(node):
    return node[0]


def _fn(node):
    if _has_children(node):
        return node[1][0]
    else:
        return node[1]


def tree_path(target, tree):
    if _name(tree) == target:
        return []
    else:
        for i in _children(tree).items():
            found = tree_path(target, i)
            if not (found is None):
                return [_name(i)] + found
        return None


def tree_find(tree, path=None):
    if not path:
        path = []
    plain_node = [_fn(tree)]
    if path:
        return plain_node + tree_find(_get_child(tree, path[0]), path[1:])
    else:
        return plain_node


def tree_graft(target, branches, tree=None):
    if not tree:
        tree = nav_tree
    path = tree_path(target, tree)
    new_tree = deepcopy(tree)
    node = new_tree
    for idx in path:
        node = _children(node).get(idx)
    if _has_children(node):
        node[1] = [node[1], dict(_children(node).items() + branches.items())]
    else:
        node[1] = [node[1], branches]
    return new_tree


def navigate(tree, end, start=None):
    steps = tree_find(tree, tree_path(end, tree))
    if steps is None:
        raise ValueError("Destination not found in navigation tree: %s" % end)
    if start:
        steps = dropwhile(lambda s: _name(s) != start, steps)
        if len(steps) == 0:
            raise ValueError("Starting location %s not found in navigation tree." % start)
    for step in steps:
        step()


def add_branch(target, branches):
    global nav_tree
    nav_tree = tree_graft(target, branches)


def go_to(dest, start=None):
    navigate(nav_tree, dest, start)


def move_to_fn(el):
    return lambda: move_to_element(el)


def click_fn(el):
    return lambda: click(el)
