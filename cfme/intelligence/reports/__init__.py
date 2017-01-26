# -*- coding: utf-8 -*-
"""This is a directory of modules, each one represents one accordion item.

  * :py:mod:`cfme.intelligence.reports.reports`
  * :py:mod:`cfme.intelligence.reports.schedules`
  * :py:mod:`cfme.intelligence.reports.import_export`
  * :py:mod:`cfme.intelligence.reports.saved`
  * :py:mod:`cfme.intelligence.reports.widgets`
  * :py:mod:`cfme.intelligence.reports.dashboards`
"""
from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.web_ui import accordion
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep


class Report(Navigatable):
    """
        This is fake class mainly needed for navmazing navigation

    """
    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance)


@navigator.register(Report, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Cloud Intel', 'Reports')


@navigator.register(Report, 'SavedReports')
class SavedReports(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Saved Reports", "All Saved Reports")


@navigator.register(Report, 'Reports')
class Reports(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Reports", "All Reports")


@navigator.register(Report, 'Schedules')
class Schedules(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Schedules", "All Schedules")


@navigator.register(Report, 'Dashboards')
class Dashboards(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Dashboards", "All Dashboards")


@navigator.register(Report, 'DashboardWidgets')
class DashboardWidgets(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Dashboard Widgets", "All Widgets")


@navigator.register(Report, 'EditReportMenus')
class EditReportMenus(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Edit Report Menus", "All EVM Groups")


@navigator.register(Report, 'ImportExport')
class ImportExport(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Import/Export", "Import / Export")
