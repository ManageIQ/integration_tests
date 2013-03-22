#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestTasks:
    def test_tasks(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        tasks_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Tasks").click()
        Assert.true(tasks_pg.is_the_current_page)

        Assert.true(len(tasks_pg.tabbutton_region.tabbuttons) == 4, "Should be 4 items")

        tasks_pg.tabbutton_region.tabbuttons[1].click()
        name = tasks_pg.tabbutton_region.tabbuttons[1].name

        string = "Name should be 'My Other UI Tasks' instead of '%s'" % name

        Assert.true(name == "My Other UI Tasks", string)
