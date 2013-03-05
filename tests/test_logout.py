'''
Created on Mar 5, 2013

@author: bcrochet
'''

import pytest
from unittestzero import Assert

class TestLogout:
    @pytest.mark.nondestructive
    def test_logout(self, mozwebqa, home_page_logged_in):
        login_pg = home_page_logged_in.header.logout()
        Assert.true(login_pg.is_the_current_page, "Not on login page")