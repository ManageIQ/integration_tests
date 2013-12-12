#!/usr/bin/env python
'''
@author: unknown
'''
# -*- coding: utf-8 -*-
# pylint: disable=E1101
import pytest
from unittestzero import Assert


@pytest.fixture(scope="module",
                params=["rhevm32"])
def infra_provider(request, cfme_data):
    '''Return the data for a particular provider'''
    param = request.param
    return cfme_data["management_systems"][param]


@pytest.mark.usefixtures("maximized", "setup_infrastructure_providers")
@pytest.mark.nondestructive
class TestPolicy:
    def test_policy_assignment(self, infra_providers_pg, infra_provider):
        '''
        Assigns policy profile(s) defined in cfme_data to management system

        Requires management system and a policy profile to assign
        '''
        prov_pg = infra_providers_pg
        Assert.true(prov_pg.is_the_current_page)
        prov_pg.select_provider(infra_provider["name"])
        policy_pg = prov_pg.click_on_manage_policies()
        for profile in infra_provider["policy_profiles"]:
            policy_pg.select_profile_item(profile)
        policy_pg.save()
        Assert.true(policy_pg.flash.message.startswith(
                'Policy assignments successfully changed'))
