#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestSmartProxies:
    def test_smartproxies(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        smartproxies_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("SmartProxies").click()
        Assert.true(smartproxies_pg.is_the_current_page)
