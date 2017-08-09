# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.utils import Parameter
from widgetastic.widget import View
from widgetastic_manageiq import ManageIQTree, MultiBoxSelect
from widgetastic_patternfly import Accordion, Button, Dropdown, FlashMessages

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.web_ui import accordion
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep


class CloudIntelReportsView(BaseLoggedInPage):
    flash = FlashMessages('.//div[starts-with(@id, "flash_text_div")]')

    @property
    def in_intel_reports(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Cloud Intel", "Reports"])

    @property
    def is_displayed(self):
        return self.in_intel_reports and self.configuration.is_displayed

    @View.nested
    class saved_reports(Accordion):  # noqa
        ACCORDION_NAME = "Saved Reports"
        tree = ManageIQTree()

    @View.nested
    class reports(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class schedules(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class dashboards(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class dashboard_widgets(Accordion):  # noqa
        ACCORDION_NAME = "Dashboard Widgets"
        tree = ManageIQTree()

    @View.nested
    class edit_report_menus(Accordion):  # noqa
        ACCORDION_NAME = "Edit Report Menus"

        tree = ManageIQTree()

    @View.nested
    class import_export(Accordion):  # noqa
        ACCORDION_NAME = "Import/Export"

        tree = ManageIQTree()

    configuration = Dropdown("Configuration")


@navigator.register(Server)
class CloudIntelReports(CFMENavigateStep):
    VIEW = CloudIntelReportsView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self):
        self.view.navigation.select("Cloud Intel", "Reports")


class ReportsMultiBoxSelect(MultiBoxSelect):
    move_into_button = Button(title=Parameter("@move_into"))
    move_from_button = Button(title=Parameter("@move_from"))


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
