# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.destructive
@pytest.mark.usefixtures("maximized")
class TestAutomate:
    def test_reset_automate(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        ms_pg = home_pg.header.site_navigation_menu("Automate").sub_navigation_menu("Import / Export").click()
        Assert.true(ms_pg.is_the_current_page)
        ms_pg = ms_pg.reset_automate()
        Assert.true(ms_pg.flash.message == "All custom classes and instances have been reset to default")

