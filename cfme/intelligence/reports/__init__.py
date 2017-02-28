# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_manageiq import ManageIQTree
from widgetastic_patternfly import Accordion, Dropdown, FlashMessages

from cfme import BaseLoggedInPage
from cfme.base import Server
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
