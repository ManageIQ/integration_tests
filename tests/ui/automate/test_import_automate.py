# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
import os

# TODO: get import files via http
@pytest.fixture(scope="module",
                params=["datastore.xml"])
def import_automate_file(request):
    automate_file = "%s/tests/ui/automate/%s" % (os.getcwd(), request.param)
    return automate_file

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestAutomate:
    def test_import_automate(self, mozwebqa, home_page_logged_in, import_automate_file):
        home_pg = home_page_logged_in
        ms_pg = home_pg.header.site_navigation_menu("Automate").sub_navigation_menu("Import / Export").click()
        Assert.true(ms_pg.is_the_current_page)
        ms_pg = ms_pg.import_automate(import_automate_file)
        Assert.true(ms_pg.flash.message == "Import file was uploaded successfully")

