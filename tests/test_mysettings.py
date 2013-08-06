#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
class TestMySettings:
    def test_mysettings(self, cnf_mysettings_pg):
        Assert.true(cnf_mysettings_pg.is_the_current_page)

        Assert.equal(len(cnf_mysettings_pg.tabbutton_region.tabbuttons),
                4, "Should be 4 items")

        cnf_mysettings_pg.tabbutton_region.tabbuttons[1].click()
        name = cnf_mysettings_pg.tabbutton_region.tabbuttons[1].name

        string = "Name should be 'Default Views' instead of %s" % name

        Assert.equal(name, "Default Views", string)
