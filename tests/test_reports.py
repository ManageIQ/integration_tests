#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert
import os

@pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive
class TestReports:
    def test_import_reports(self, intel_reports_pg):
        report_file = "sample_reports.yaml"
        reports = "%s/tests/%s" % (os.getcwd(), report_file)

        Assert.true(intel_reports_pg.is_the_current_page)
        import_pg = intel_reports_pg.click_on_import_export()
        import_pg = import_pg.import_reports(reports)
        Assert.true(any(import_pg.flash.message.startswith(m)
                for m in ["Imported Report", "Replaced Report"]))
