#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestNavigation:
    @pytest.mark.usefixtures('maximized')
    def test_navigation(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        Assert.true(home_pg.is_logged_in, "Could not determine if logged in")
        infra_pg = home_pg.header.site_navigation_menu("Infrastructure").click()
        Assert.true(infra_pg.is_the_current_page)
        pxe_pg = infra_pg.header.site_navigation_menu(
                "Infrastructure").sub_navigation_menu("PXE").click()
        Assert.true(pxe_pg.is_the_current_page)
        prov_pg = pxe_pg.header.site_navigation_menu(
                "Infrastructure").sub_navigation_menu("Providers").click()
        Assert.true(prov_pg.is_the_current_page)
        config_pg = prov_pg.header.site_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        vm_pg = config_pg.header.site_navigation_menu(
                "Infrastructure").sub_navigation_menu("Virtual Machines").click()
        Assert.true(vm_pg.is_the_current_page)
        from pages.infrastructure_subpages.vms_subpages.virtual_machines import VirtualMachines
        Assert.true(type(vm_pg) is VirtualMachines)
