#!/usr/bin/env python

import pytest
from unittestzero import Assert
from pages.login import login_admin, login
from pages.dashboard import dashboard_page
from fixtures.configuration import conf


@pytest.mark.nondestructive  # IGNORE:E1101
@pytest.mark.usefixtures("selenium")
def test_login():
    login_admin()
    Assert.true(dashboard_page.is_displayed(), "Could not determine if logged in")


def test_bad_password():
    try:
        login(conf.get_in('cmfe', 'admin_user'), "badpassword@#$")
    cat
    
