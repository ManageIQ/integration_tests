# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
class TestAccordion:
    def test_accordion(self, infra_vms_pg):
        Assert.true(infra_vms_pg.is_the_current_page)
        Assert.equal(len(infra_vms_pg.accordion.accordion_items), 3,
                "Should be 3 accordion items")
        infra_vms_pg.accordion.accordion_items[1].click()
        name = infra_vms_pg.accordion.accordion_items[1].name
        Assert.equal(name, "VMs", "Name should be 'VMs'")
        infra_vms_pg.accordion.accordion_items[2].click()
        name = infra_vms_pg.accordion.accordion_items[2].name
        Assert.not_equal(name, "VMs", "Name should NOT be 'VMs'")

