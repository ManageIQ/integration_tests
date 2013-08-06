#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
class TestSettings:
    def test_settings(self, cnf_configuration_pg):
        Assert.true(cnf_configuration_pg.is_the_current_page)

        Assert.equal(len(cnf_configuration_pg.tabbutton_region.tabbuttons),
                8, "Should be 8 items")

        cnf_configuration_pg.tabbutton_region.tabbuttons[2].click()
        name = cnf_configuration_pg.tabbutton_region.tabbuttons[2].name

        Assert.equal(name, "Workers", "Name should be 'Workers'")
