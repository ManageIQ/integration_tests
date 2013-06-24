#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert


@pytest.fixture(scope="module",  # IGNORE:E1101
                params=["rhevm31"])
def management_system(request, cfme_data):
    param = request.param
    return cfme_data.data["management_systems"][param]


@pytest.mark.usefixtures("maximized", "setup_mgmt_systems")
@pytest.mark.nondestructive  # IGNORE:E1101
class TestPolicy:
    def test_policy_assignment(self, mozwebqa, home_page_logged_in, management_system):
        '''
        Assigns policy profile(s) defined in cfme_data to management system

        Requires management system and a policy profile to assign
        '''
        home_pg = home_page_logged_in
        mgmt_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
        Assert.true(mgmt_pg.is_the_current_page)
        mgmt_pg.select_management_system(management_system["name"])
        policy_pg = mgmt_pg.click_on_manage_policies()
        for profile in management_system["policy_profiles"]:
            policy_pg.select_profile_item(profile)
        policy_pg.save()
        Assert.true(policy_pg.flash.message.startswith('Policy assignments successfully changed'))
