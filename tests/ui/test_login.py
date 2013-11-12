#!/usr/bin/env python

import pytest
from unittestzero import Assert
from pages.login import login_page, login_admin
from fixtures.configuration import conf


@pytest.mark.nondestructive  # IGNORE:E1101
@pytest.mark.usefixtures("selenium")
def test_login():
    login_admin()
    Assert.true(login_page.is_displayed(), "Could not determine if logged in")
