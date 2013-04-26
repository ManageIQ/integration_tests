#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert


@pytest.fixture(scope="module",
                # pasted in from running 'print_default_actions'
                params=['Datastore Analysis Complete',
                'Datastore Analysis Request'])

def expected_events(request):
    return request.param

@pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive
class TestEvents:
    def test_default_events(self, mozwebqa, home_page_logged_in, expected_events):
        home_pg = home_page_logged_in
        explore_pg = home_pg.header.site_navigation_menu("Control").sub_navigation_menu("Explorer").click()
        Assert.true(explore_pg.is_the_current_page)
        events_pg = explore_pg.click_on_events_accordion()
        Assert.true(expected_events in events_pg.events_list)

