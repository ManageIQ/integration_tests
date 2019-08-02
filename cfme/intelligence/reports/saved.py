# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Text

from cfme.intelligence.reports import CloudIntelReportsView
from cfme.intelligence.reports.reports import SavedReportDetailsView as BaseSavedReportDetailsView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import Table


class AllSavedReportsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    table = Table(".//div[@id='records_div' or @id='main_div']//table")
    paginator = PaginationPane()

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.saved_reports.is_opened and
            self.saved_reports.tree.currently_selected == ["All Saved Reports"] and
            self.title.text == "All Saved Reports"
        )


class SavedReportDetailsView(BaseSavedReportDetailsView):
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


@attr.s
class SavedReport(BaseEntity):
    name = attr.ib()
    run_at_datetime = attr.ib()
    queued_datetime_in_title = attr.ib()

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

    @property
    def tree_path(self):
        return [
            "Saved Reports",
            "All Saved Reports",
            self.name,
            self.run_at_datetime
        ]


@attr.s
class SavedReportsCollection(BaseCollection):
    ENTITY = SavedReport


@navigator.register(SavedReportsCollection, "All")
class CustomReportAll(CFMENavigateStep):
    VIEW = AllSavedReportsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self, *args, **kwargs):
        self.prerequisite_view.saved_reports.tree.click_path("All Saved Reports")


@navigator.register(SavedReport, "Details")
class ScheduleDetails(CFMENavigateStep):
    VIEW = SavedReportDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.view.saved_reports.tree.click_path(*self.obj.tree_path)
