# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestAccordion:
    def test_accordion(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        vm_pg = home_pg.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
        Assert.true(vm_pg.is_the_current_page)
        Assert.true(len(vm_pg.accordion.accordion_items) == 3, "Should be 3 accordion items")
        vm_pg.accordion.accordion_by_name('My VMs').click()
        tree = vm_pg.accordion.current_content
        Assert.true(tree.children[0].children[4].name == "Environment / Prod")
        did_collapse = tree.children[0].twisty.collapse()
        Assert.true(did_collapse, "Was not collapsible, or was already collapsed")        
