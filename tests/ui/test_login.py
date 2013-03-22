#!/usr/bin/env python

import pytest
import time
from unittestzero import Assert
from pages.login import LoginPage

@pytest.mark.nondestructive
class TestLogin:
    def test_login(self, mozwebqa):
        login_pg = LoginPage(mozwebqa)
        login_pg.go_to_login_page()
        home_pg = login_pg.login()
        Assert.true(home_pg.is_logged_in, "Could not determine if logged in")
