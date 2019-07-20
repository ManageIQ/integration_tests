# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling
from widgetastic.utils import Parameter
from widgetastic.widget import View
from widgetastic_patternfly import Accordion
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import MultiBoxSelect


class CloudIntelReportsView(BaseLoggedInPage):
    mycompany_title = "My Company (All Groups)"

    @property
    def in_intel_reports(self):
        return (
            self.logged_in_as_current_user
            and self.navigation.currently_selected
            == [self.context["object"].appliance.server.intel_name, "Reports"]
        )

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

    def step(self, *args, **kwargs):
        self.view.navigation.select(self.view.context["object"].intel_name, "Reports")

    def resetter(self, *args, **kwargs):
        self.view.saved_reports.open()


class ReportsMultiBoxSelect(MultiBoxSelect):
    move_into_button = Button(title=Parameter("@move_into"))
    move_from_button = Button(title=Parameter("@move_from"))
