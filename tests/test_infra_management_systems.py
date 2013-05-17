#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.fixture(scope="module",  # IGNORE:E1101
        params=["VMware vCenter", "Red Hat Enterprise Virtualization Manager"])
def management_system_type(request):
    return request.param

@pytest.fixture(params=["test_name_2"])  # IGNORE:E1101
def management_system_name(request):
    return request.param

@pytest.fixture  # IGNORE:E1101
def mgmtsys_pg(home_page_logged_in):
    return home_page_logged_in.header.site_navigation_menu(
            "Infrastructure").sub_navigation_menu("Management Systems").click()

@pytest.mark.nondestructive  # IGNORE:E1101
class TestManagementSystems:
    def test_management_systems(self,
            mozwebqa,
            mgmtsys_pg,
            management_system_name,
            management_system_type):
        management_pg = mgmtsys_pg
        Assert.true(management_pg.is_the_current_page)

        new_ms_pg = management_pg.click_on_add_new_management_system()

        new_ms_pg.select_management_system_type(management_system_type)

        new_ms_pg.new_management_system_fill_data(name=management_system_name)

        management_pg = new_ms_pg.click_on_cancel()
        Assert.true(management_pg.is_the_current_page)
