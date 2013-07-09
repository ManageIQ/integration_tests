#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive  # IGNORE:E1101
class TestNavigation:
    def test_navigation(self, home_page_logged_in):
        home_pg = home_page_logged_in
        infra_pg = home_pg.header.site_navigation_menu("Infrastructure").click()
        Assert.true(infra_pg.is_the_current_page)
        pxe_pg = infra_pg.header.site_navigation_menu(
                "Infrastructure").sub_navigation_menu("PXE").click()
        Assert.true(pxe_pg.is_the_current_page)
        prov_pg = pxe_pg.header.site_navigation_menu(
                "Infrastructure").sub_navigation_menu("Providers").click()
        Assert.true(prov_pg.is_the_current_page)
