from cfme.fixtures.soft_assert import soft_assert
from cfme.utils.appliance.implementations.ui import navigate_to


def traverse(dic, paths, path=None):
    path = path or []
    if isinstance(dic, list):
        for item in dic:
            np = path[:]
            np.append(item)
            paths.append(np)
    elif isinstance(dic, dict):
        for k, v in dic.items():
            np = path[:]
            np.append(k)
            traverse(v, paths, np)
    return paths


def test_each_page(appliance):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: None
    """
    view = navigate_to(appliance.server, 'Dashboard')
    # test meta is here and CFME will be displayed correctly in IE11
    edge_header = view.browser.element('//meta[@content="IE=edge"]')
    soft_assert(edge_header.get_attribute('http-equiv') == 'X-UA-Compatible')
    tree = view.navigation.nav_item_tree()
    paths = []
    traverse(tree, paths, path=None)
    for link in paths:
        view.navigation.select(*link)
