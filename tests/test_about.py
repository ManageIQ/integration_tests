#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive
class TestAbout:
    def test_about(self, cnf_about_pg):
        Assert.true(cnf_about_pg.is_the_current_page)
