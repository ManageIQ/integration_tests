# -*- coding: utf-8 -*-
from functools import partial
from navmazing import NavigateToSibling, NavigateToObject

from . import Report
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, accordion, toolbar
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.appliance import Navigatable

reports_table = CheckboxTable("//div[@id='records_div']//table[thead]")
cfg_btn = partial(toolbar.select, "Configuration")


class SavedReport(Navigatable):

    def __init__(self, name, timestamp, appliance=None):
        Navigatable.__init__(self, appliance)
        self.name = name
        self.timestamp = timestamp

    def delete(self, cancel):
        navigate_to(self, 'Delete')
        sel.handle_alert(cancel)

    @classmethod
    def get_all_saved_reports_by_name(cls, name):
        navigate_to(cls, 'All')
        accordion.tree("Saved Reports", "All Saved Reports", name)
        dates = []
        try:
            for row in reports_table.rows():
                dates.append(sel.text(row.queued_at).encode("utf-8").strip())
        except sel.NoSuchElementException:
            pass
        return dates

    def go_to_latest_saved_report(self):
        latest = self.get_all_saved_reports_by_name(self.name)[0]
        navigate_to(self, 'Details')
        reports_table.click_cell("queued_at", latest)


@navigator.register(SavedReport, 'All')
class SavedReportAll(CFMENavigateStep):
    prerequisite = NavigateToObject(Report, 'SavedReports')


@navigator.register(SavedReport, 'Details')
class ScheduleDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Saved Reports", "All Saved Reports", self.obj.name, self.obj.timestamp)


@navigator.register(SavedReport, 'Delete')
class ScheduleDelete(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn("Delete this Saved Report from the Database", invokes_alert=True)
