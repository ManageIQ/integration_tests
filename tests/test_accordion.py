# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestAccordion:
    def test_accordion(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        Assert.true(home_pg.is_logged_in, "Could not determine if logged in")
        vm_pg = home_pg.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
        Assert.true(vm_pg.is_the_current_page)
        Assert.true(len(vm_pg.accordion.accordion_items) == 3, "Should be 3 accordion items")
        vm_pg.accordion.accordion_items[1].click()
        name = vm_pg.accordion.accordion_items[1].name
        Assert.true(name == "My VMs", "Name should be 'My VMs'")
        vm_pg.accordion.accordion_items[2].click()
        name = vm_pg.accordion.accordion_items[2].name
        Assert.false(name == "My VMs", "Name should NOT be 'My VMs'")
        