#!/usr/bin/env python

import pytest
from unittestzero import Assert
from pages.login import login_page, login_admin
from pages.dashboard import dashboard_page
from fixtures.configuration import conf


@pytest.mark.nondestructive  # IGNORE:E1101
@pytest.mark.usefixtures("selenium")
def test_login():
    login_admin()
    Assert.true(dashboard_page.is_displayed(), "Could not determine if logged in")
