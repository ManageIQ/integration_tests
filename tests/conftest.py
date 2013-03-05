'''
Created on Mar 4, 2013

@author: bcrochet
'''

import pytest
from unittestzero import Assert

@pytest.fixture
def home_page_logged_in(mozwebqa):
    from pages.login import LoginPage
    login_pg = LoginPage(mozwebqa)
    login_pg.go_to_login_page()
    home_pg = login_pg.login()
    Assert.true(home_pg.is_logged_in, "Could not determine if logged in")
    return home_pg

@pytest.fixture
def maximized(mozwebqa):
    mozwebqa.selenium.maximize_window()
    return True
