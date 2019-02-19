# -*- coding: utf-8 -*-
from navmazing import NavigateToAttribute
from widgetastic.widget import Checkbox
from widgetastic.widget import ClickableMixin
from widgetastic.widget import Select
from widgetastic.widget import Text
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from . import CloudIntelReportsView
from cfme.base.ui import Server
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Table


class InputButton(Input, ClickableMixin):
    pass


class ImportExportCommonForm(CloudIntelReportsView):

    title = Text("#explorer_title_text")
    subtitle = Text(locator=".//div[@id='main_div']/h2")
    upload_file = Input("upload[file]")
    items_for_export = Select(id="choices_chosen")

    upload_button = InputButton("commit")
    export_button = Button("Export")


class ImportExportCustomReportsView(ImportExportCommonForm):

    overwrite = Checkbox("overwrite")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == "Import / Export" and
            self.subtitle.text == "Custom Reports" and
            self.import_export.tree.currently_selected == ["Import / Export", "Custom Reports"]
        )


class ImportExportWidgetsView(ImportExportCommonForm):

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == "Import / Export" and
            self.subtitle.text == "Widgets" and
            self.import_export.tree.currently_selected == ["Import / Export", "Widgets"]
        )


class ImportExportWidgetsCommitView(CloudIntelReportsView):

    title = Text("#explorer_title_text")
    table = Table(".//form[@id='import-widgets-form']/table")
    commit_button = InputButton("commit")
    cancel_button = InputButton("cancel")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == "Import / Export" and
            self.import_export.tree.currently_selected == ["Import / Export", "Widgets"]
        )


@navigator.register(Server)
class ImportExportCustomReports(CFMENavigateStep):
    VIEW = ImportExportCustomReportsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self, *args, **kwargs):
        self.view.import_export.tree.click_path("Import / Export", "Custom Reports")


@navigator.register(Server)
class ImportExportWidgets(CFMENavigateStep):
    VIEW = ImportExportWidgetsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self, *args, **kwargs):
        self.view.import_export.tree.click_path("Import / Export", "Widgets")
