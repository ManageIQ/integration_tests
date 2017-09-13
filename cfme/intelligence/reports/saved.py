# -*- coding: utf-8 -*-
from widgetastic.widget import Text
from widgetastic_manageiq import Table, PaginationPane
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from navmazing import NavigateToSibling

from . import CloudIntelReportsView
from .reports import CustomSavedReportDetailsView


class AllSavedReportsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    table = Table(".//div[@id='records_div']/table")
    paginator = PaginationPane()

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.saved_reports.is_opened and
            self.saved_reports.tree.currently_selected == ["All Saved Reports"] and
            self.title.text == "All Saved Reports"
        )


class SavedReportDetailsView(CustomSavedReportDetailsView):

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.saved_reports.is_opened and
            self.saved_reports.tree.currently_selected == ([
                "All Reports",
                self.context["object"].name,
                self.context["object"].run_at_datetime
            ]) and
            self.title.text == 'Saved Report "{}"'.format(self.context["object"].name)
        )


class SavedReportView(AllSavedReportsView):

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.saved_reports.is_opened and
            self.saved_reports.tree.currently_selected == [
                "All Saved Reports",
                self.context["object"].name
            ] and
            self.title.text == 'Saved Report "{}"'.format(self.context["object"].name)
        )


class SavedReport(Navigatable):

    def __init__(self, name, run_at_datetime, queued_datetime_in_title, appliance=None):
        Navigatable.__init__(self, appliance)
        self.name = name
        self.run_at_datetime = run_at_datetime
        self.queued_datetime_in_title = queued_datetime_in_title

    def delete(self, cancel=False):
        view = navigate_to(self, "Details")
        view.configuration.item_select(
            "Delete this Saved Report from the Database",
            handle_alert=not cancel
        )
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view.flash.assert_no_error()
            view.flash.assert_message("Successfully deleted Saved Report from the CFME Database")


@navigator.register(SavedReport, "Details")
class ScheduleDetails(CFMENavigateStep):
    VIEW = SavedReportDetailsView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.view.saved_reports.tree.click_path(
            "Saved Reports",
            "All Saved Reports",
            self.obj.name,
            self.obj.run_at_datetime
        )
