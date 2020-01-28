import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [test_requirements.general_ui]


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


@pytest.mark.meta(coverage=[1648338])
def test_each_page(appliance, soft_assert):
    """
    Bugzilla:
        1648338

    Polarion:
        assignee: pvala
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    view = navigate_to(appliance.server, 'Dashboard')
    # no meta is present for 5.11
    if appliance.version < "5.11":
        # test meta is here and CFME will be displayed correctly in IE11
        edge_header = view.browser.element('//meta[@content="IE=edge"]')
        soft_assert(edge_header.get_attribute('http-equiv') == 'X-UA-Compatible')
    tree = view.navigation.nav_item_tree()
    paths = []
    traverse(tree, paths, path=None)
    for link in paths:
        view.navigation.select(*link)
