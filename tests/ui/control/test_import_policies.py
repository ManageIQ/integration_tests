# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
import os

# TODO: get import files via http
@pytest.fixture(scope="module",
                params=["policies.yaml"])
def import_policy_file(request):
    policy_file = "%s/%s" % (os.getcwd(), request.param)
    return policy_file

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestControl:
    def test_import_policies(self, mozwebqa, home_page_logged_in, import_policy_file):
        home_pg = home_page_logged_in
        ms_pg = home_pg.header.site_navigation_menu("Control").sub_navigation_menu("Import / Export").click()
        Assert.true(ms_pg.is_the_current_page)
        ms_pg = ms_pg.import_policies(import_policy_file)
        Assert.true(ms_pg.flash.message == "Press commit to Import")
        ms_pg = ms_pg.click_on_commit()
        Assert.true(ms_pg.flash.message == "Import file was uploaded successfully")

