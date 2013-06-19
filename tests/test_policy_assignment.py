#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

# @pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive
class TestPolicy:
    def test_policy_assignment(self, mozwebqa, home_page_logged_in):
        _mgmt_sys = "RHEVM 3.1"
        _profile_item = "Validate VM"

        home_pg = home_page_logged_in
        mgmt_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
        Assert.true(mgmt_pg.is_the_current_page)
        mgmt_pg.select_management_system(_mgmt_sys)
        policy_pg = mgmt_pg.click_on_manage_policies()
        policy_pg.select_profile_item(_profile_item)
        policy_pg.reset
        policy_pg.cancel
        Assert.true(policy_pg.flash.message.startswith('Edit policy assignments was cancelled by the user'))
