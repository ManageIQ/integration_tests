from __future__ import absolute_import
from cfme.utils.appliance.implementations.ui import navigate_to
import six


def traverse(dic, paths, path=None):
    path = path or []
    if isinstance(dic, list):
        for item in dic:
            np = path[:]
            np.append(item)
            paths.append(np)
    elif isinstance(dic, dict):
        for k, v in six.iteritems(dic):
            np = path[:]
            np.append(k)
            traverse(v, paths, np)
    return paths


def test_each_page(appliance):
    view = navigate_to(appliance.server, 'Dashboard')
    tree = view.navigation.nav_item_tree()
    paths = []
    traverse(tree, paths, path=None)
    for link in paths:
        view.navigation.select(*link)
