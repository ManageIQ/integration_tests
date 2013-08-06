#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
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
    def test_default_events(self, control_explorer_pg, expected_events):
        Assert.true(control_explorer_pg.is_the_current_page)
        events_pg = control_explorer_pg.click_on_events_accordion()
        Assert.true(expected_events in events_pg.events_list)

