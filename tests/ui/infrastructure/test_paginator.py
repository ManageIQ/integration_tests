import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
@pytest.mark.usefixtures("setup_infrastructure_providers")
class TestPaginator:
    def test_paginator(self, infra_vms_pg):
        Assert.true(infra_vms_pg.is_the_current_page)
        Assert.true(infra_vms_pg.paginator.selected_per_page, '20')
        infra_vms_pg.paginator.set_per_page('100')
        Assert.true(infra_vms_pg.paginator.selected_per_page, '100')
