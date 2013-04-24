#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
import os

@pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive
class TestReports:
    def test_import_reports(self, mozwebqa, home_page_logged_in):
        report_file = "sample_reports.yaml"
        reports = "%s/tests/%s" % (os.getcwd(), report_file)

        home_pg = home_page_logged_in
        report_pg = home_pg.header.site_navigation_menu("Virtual Intelligence").sub_navigation_menu("Reports").click()
        Assert.true(report_pg.is_the_current_page)
        import_pg = report_pg.click_on_import_export()
        import_pg = import_pg.import_reports(reports)
        Assert.true(any(import_pg.flash.message.startswith(m) for m in ["Imported Report", "Replaced Report"]))
