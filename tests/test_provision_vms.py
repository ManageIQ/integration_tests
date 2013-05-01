'''
Created on May 1, 2013

@author: bcrochet
'''
# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive  # IGNORE:E1101
class TestProvisionVms:
    def test_provision_start(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        vm_pg = home_pg.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
        Assert.true(vm_pg.is_the_current_page)
        vmstart_pg = vm_pg.click_on_provision_vms()

        for item in vmstart_pg.template_region.templates:
            print item.name
            print item.operating_system
            print item.platform

        vm_pg = vmstart_pg.click_on_cancel()
        Assert.true(vm_pg.is_the_current_page)
