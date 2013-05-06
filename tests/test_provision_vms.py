'''
Created on May 1, 2013

@author: bcrochet
'''
# -*- coding: utf-8 -*-

import pytest
import time
import random
from unittestzero import Assert

@pytest.fixture  # IGNORE:E1101
def vm_page(request,mozwebqa,home_page_logged_in):
    return home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()

@pytest.mark.nondestructive  # IGNORE:E1101
class TestProvisionVms:
    def test_provision_start(self, mozwebqa, vm_page):
        vm_pg = vm_page
        Assert.true(vm_pg.is_the_current_page)
        vmstart_pg = vm_pg.click_on_provision_vms()

        for item in vmstart_pg.template_list.items:
            print item.name
            print item.operating_system
            print item.platform

        vm_pg = vmstart_pg.click_on_cancel()
        Assert.true(vm_pg.is_the_current_page)
        
    def test_provision_continue(self, mozwebqa, vm_page):
        vm_pg = vm_page
        Assert.true(vm_pg.is_the_current_page)
        vmstart_pg = vm_pg.click_on_provision_vms()
        number_of_templates = len(vmstart_pg.template_list.templates)
        template = random.randint(0, number_of_templates)
        vmstart_pg.template_list.templates[template].click()
        prov_pg = vmstart_pg.click_on_continue()
        prov_pg.click_on_cancel()
