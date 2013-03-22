#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestMySettings:
    def test_mysettings(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        settings_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("My Settings").click()
        Assert.true(settings_pg.is_the_current_page)

        Assert.true(len(settings_pg.tabbutton_region.tabbuttons) == 4, "Should be 4 items")

        settings_pg.tabbutton_region.tabbuttons[1].click()
        name = settings_pg.tabbutton_region.tabbuttons[1].name

        string = "Name should be 'Default Views' instead of %s" % name

        Assert.true(name == "Default Views", string)
