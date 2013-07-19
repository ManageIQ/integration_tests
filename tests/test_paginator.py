# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestPaginator:
    def test_paginator(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        Assert.true(home_pg.is_logged_in, "Could not determine if logged in")
        vm_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Virtual Machines").click()
        Assert.true(vm_pg.is_the_current_page)
        Assert.true(vm_pg.paginator.selected_per_page, '20')
        vm_pg.paginator.set_per_page('100')
        time.sleep(5)
        Assert.true(vm_pg.paginator.selected_per_page, '100')
