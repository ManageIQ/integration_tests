#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestSettings:
    def test_settings(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)

        Assert.true(len(config_pg.tabbutton_region.tabbuttons) == 8, "Should be 8 items")

        config_pg.tabbutton_region.tabbuttons[2].click()
        name = config_pg.tabbutton_region.tabbuttons[2].name

        Assert.true(name == "Workers", "Name should be 'Workers'")
