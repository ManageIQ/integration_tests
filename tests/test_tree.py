'''
@author: bcrochet
'''
# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

# pylint: disable=E1101

@pytest.mark.nondestructive
def test_tree(infra_vms_pg):
    '''Test the tree control'''
    Assert.true(infra_vms_pg.is_the_current_page)
    Assert.equal(len(infra_vms_pg.accordion.accordion_items), 3,
            "Should be 3 accordion items")
    accordions = ['VMs & Templates', 'VMs', 'Templates']
    for accordion in accordions:
        infra_vms_pg.accordion.accordion_by_name(accordion).click()
    infra_vms_pg.accordion.accordion_by_name('VMs').click()
    tree = infra_vms_pg.accordion.current_content
    Assert.true(tree.children[0].children[5].name == "Environment / Test")
    did_collapse = tree.children[0].twisty.collapse()
    Assert.true(did_collapse, "Was not collapsible, or was already collapsed")
    node = tree.find_node_by_name("Environment / Prod")
    Assert.equal("Environment / Prod", node.name)
