#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.fixture(scope="module",
                # pasted in from running 'print_default_actions'
                params=[('Cancel vCenter Task', 'Cancel vCenter Task'),
    ('Check Host or VM Compliance', 'Check Host or VM Compliance')])

def expected_action(request):
    return request.param

@pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive
class TestActions:
    def test_default_actions(self, mozwebqa, home_page_logged_in, expected_action):
        home_pg = home_page_logged_in
        explore_pg = home_pg.header.site_navigation_menu("Control").sub_navigation_menu("Explorer").click()
        Assert.true(explore_pg.is_the_current_page)
        actions_pg = explore_pg.click_on_actions_accordion()
        Assert.true(expected_action in actions_pg.actions_list())

    def test_create_invalid_action(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        explore_pg = home_pg.header.site_navigation_menu("Control").sub_navigation_menu("Explorer").click()
        Assert.true(explore_pg.is_the_current_page)
        actions_pg = explore_pg.click_on_actions_accordion()
        Assert.true(actions_pg.is_the_current_page)
        new_actions_pg = actions_pg.click_on_add_new()
        new_actions_pg = new_actions_pg.add_invalid_action()
        Assert.true(new_actions_pg.flash.message == "Action Type must be selected")

