'''
@author: bcrochet
'''
# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

# pylint: disable=E1101

@pytest.mark.nondestructive
def test_tree(home_page_logged_in):
    '''Test the tree control'''
    home_pg = home_page_logged_in
    vm_pg = home_pg.header.site_navigation_menu(
            "Infrastructure").sub_navigation_menu("Virtual Machines").click()
    Assert.true(vm_pg.is_the_current_page)
    Assert.equal(len(vm_pg.accordion.accordion_items), 3,
            "Should be 3 accordion items")
    vm_pg.accordion.accordion_by_name('My VMs').click()
    tree = vm_pg.accordion.current_content
    Assert.true(tree.children[0].children[5].name == "Environment / Test")
    did_collapse = tree.children[0].twisty.collapse()
    Assert.true(did_collapse, "Was not collapsible, or was already collapsed")
    node = tree.find_node_by_name("Environment / Prod")
    Assert.equal("Environment / Prod", node.name)
