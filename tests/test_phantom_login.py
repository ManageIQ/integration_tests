'''
Test for the phantom login
'''
# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert
from pages.login import LoginPage

@pytest.mark.xfail(run=True)
@pytest.mark.nondestructive
def test_that_checks_for_phantom_login(mozwebqa):
    login_pg = LoginPage(mozwebqa)
    login_pg.go_to_login_page()
    next_pg = login_pg.login_and_send_window_size()
    Assert.not_equal(next_pg.get_context_current_page(), '/',
        "This is still the login page")

