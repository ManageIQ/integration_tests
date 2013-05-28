#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive
class TestAbout:
    def test_about(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        about_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("About").click()
        Assert.true(about_pg.is_the_current_page)
