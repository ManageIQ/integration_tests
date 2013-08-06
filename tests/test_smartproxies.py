#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

# TODO: Needs more test

@pytest.mark.nondestructive
class TestSmartProxies:
    def test_smartproxies(self, cnf_smartproxies_pg):
        Assert.true(cnf_smartproxies_pg.is_the_current_page)
