"""A library for UI Automation to navigate a hierarchical interface.

Each part of the interface that is activated by a certain action, can be a
node in a tree.  For example, a website can be a tree of pages, where the root
is the home page, and each node is the name of the page and a function that gets
the browser from the parent to the current page.

A navigation node is a tuple (or dict entry), first item a string name of the node,
2nd item either a function to navigate with, or a list of a function and a dict
containing other nodes.

.. moduleauthor:: Jeff Weiss <jweiss@redhat.com>
"""
from __future__ import unicode_literals
from itertools import dropwhile
from copy import deepcopy
import functools


class UINavigate(object):
    def __init__(self):
        self.nav_tree = ['toplevel', lambda _: None]

    @staticmethod
    def _has_children(node):
        return (isinstance(node[1], (list, tuple)) and len(node[1]) > 1)

    @classmethod
    def _children(cls, node):
        if cls._has_children(node):
            return node[1][1]
        else:
            return {}

    @classmethod
    def _get_child(cls, node, name):
        return [name, cls._children(node).get(name)]

    @staticmethod
    def _name(node):
        return node[0]

    @classmethod
    def _fn(cls, node):
        if cls._has_children(node):
            return node[1][0]
        else:
            return node[1]

    @classmethod
    def tree_path(cls, target, tree):
        if cls._name(tree) == target:
            return []
        else:
            for i in cls._children(tree).items():
                found = cls.tree_path(target, i)
                if not (found is None):
                    return [cls._name(i)] + found
            return None

    @classmethod
    def tree_find(cls, tree, path=None):
        if not path:
            path = []
        plain_node = [cls._fn(tree)]
        if path:
            return plain_node + cls.tree_find(cls._get_child(tree, path[0]), path[1:])
        else:
            return plain_node

    def tree_graft(self, target, branches, tree=None):
        """Add a branch of navigation nodes to the navigation tree.

        target: str name of node to add branches to
        branches: dict of nodes that can be directly navigated to from the target.
        tree: An existing tree to graft onto. By default, graft onto the module's
        top-level tree.

        returns a new tree with branches added (does not modify existing tree)
        """
        if not tree:
            tree = self.nav_tree
        path = self.tree_path(target, tree)
        if path is None:
            raise LookupError("Unable to find target {} in nav tree.".format(target))
        new_tree = deepcopy(tree)
        parent_node = None
        node = new_tree
        for idx in path:
            parent_node = node
            node = [idx, self._children(node).get(idx)]
            if node is None:
                raise LookupError("Unable to find node {} in nav tree.".format(idx))
        if not parent_node:
            if self._has_children(node):
                self._children(node).update(branches)
            else:
                node[1] = [node[1], branches]
        elif self._has_children(node):
            self._children(
                self._get_child(
                    parent_node, self._name(node))).update(branches)
        else:
            parent_node[1][1][self._name(node)] = [node[1], branches]
        return new_tree

    @classmethod
    def navigate(cls, tree, end, start=None, context=None):
        """Navigates the tree from the start node to the end node.

        tree: A navigation tree
        end: str name of the destination node
        start: str name of the starting node (if the UI's
        current state is already known, otherwise start from
        the root node)
        context: a dict of context data.  Usually this is dynamic application data
        for example, something you just created in the UI, and now you want to
        navigate to edit it.

        """
        path = cls.tree_path(end, tree)
        if path is None:
            raise ValueError("Destination not found in navigation tree: {}".format(end))
        steps = cls.tree_find(tree, path)
        if start:
            steps = list(dropwhile(lambda s: cls._name(s) != start, steps))
            if len(steps) == 0:
                raise ValueError("Starting location {} not found in navigation tree.".format(start))
        for step in steps:
            step(context)

    def add_branch(self, target, branches):
        self.nav_tree = self.tree_graft(target, branches)

    def go_to(self, dest, start=None, context=None):
        """Navigates the module's nav_tree from start to dest.  See navigate
        function.

        """

        self.navigate(self.nav_tree, dest, start=start, context=context)

    @staticmethod
    def fn(f):
        """Takes a function of no args and makes it take 1 arg,
        making it suitable for use as a navigation step."""
        def g(_):
            return f()
        return g

    @classmethod
    def partial(cls, f, *args):
        return cls.fn(functools.partial(f, *args))
