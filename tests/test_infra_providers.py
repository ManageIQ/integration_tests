#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.fixture(scope="module",
        params=["VMware vCenter", "Red Hat Enterprise Virtualization Manager"])
def provider_type(request):
    return request.param

@pytest.fixture(params=["test_name_2"])
def provider_name(request):
    return request.param

@pytest.mark.nondestructive
def test_infrastructure_providers(
        infra_providers_pg,
        provider_name,
        provider_type):
    Assert.true(infra_providers_pg.is_the_current_page)

    new_ms_pg = infra_providers_pg.click_on_add_new_provider()

    new_ms_pg.select_provider_type(provider_type)

    new_ms_pg.new_provider_fill_data(name=provider_name)

    infra_providers_pg = new_ms_pg.click_on_cancel()
    Assert.true(infra_providers_pg.is_the_current_page)
