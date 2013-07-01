#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.fixture(scope="module",  # IGNORE:E1101
        params=["VMware vCenter", "Red Hat Enterprise Virtualization Manager"])
def provider_type(request):
    return request.param

@pytest.fixture(params=["test_name_2"])  # IGNORE:E1101
def provider_name(request):
    return request.param

@pytest.fixture  # IGNORE:E1101
def provider_pg(home_page_logged_in):
    return home_page_logged_in.header.site_navigation_menu(
            "Infrastructure").sub_navigation_menu("Providers").click()

@pytest.mark.nondestructive  # IGNORE:E1101
def test_infrastructure_providers(
        provider_pg,
        provider_name,
        provider_type):
    Assert.true(provider_pg.is_the_current_page)

    new_ms_pg = provider_pg.click_on_add_new_provider()

    new_ms_pg.select_provider_type(provider_type)

    new_ms_pg.new_provider_fill_data(name=provider_name)

    provider_pg = new_ms_pg.click_on_cancel()
    Assert.true(provider_pg.is_the_current_page)
