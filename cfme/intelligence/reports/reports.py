# -*- coding: utf-8 -*-
"""Page model for Cloud Intel / Reports / Reports"""
from cached_property import cached_property
from navmazing import NavigateToAttribute, NavigateToSibling
from utils import version
from utils.wait import wait_for
from utils.pretty import Pretty
from utils.update import Updateable
from utils.appliance import Navigatable, get_or_create_current_appliance
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from . import CloudIntelReportsView

from widgetastic.widget import Text, Checkbox, View
from widgetastic_manageiq import MultiBoxSelect, Table
from widgetastic_patternfly import Button, Input, BootstrapSelect, Tab
from cfme.web_ui.expression_editor_widgetastic import ExpressionEditor


class CustomReportFormCommon(CloudIntelReportsView):
    report_title = Text("#explorer_title_text")

    menu_name = Input("name")
    title = Input("title")
    base_report_on = BootstrapSelect("chosen_model")
    report_fields = MultiBoxSelect(
        ".//div[@id='column_lists']/table",
        move_into=Button(title="Move selected fields down"),
        move_from=Button(title="Move selected fields up"),
        available_items="available_fields",
        chosen_items="selected_fields"
    )
    cancel_after = BootstrapSelect("chosen_queue_timeout")

    @View.nested
    class consolidation(Tab):  # noqa
        column1 = BootstrapSelect("chosen_pivot1")
        column2 = BootstrapSelect("chosen_pivot2")
        column3 = BootstrapSelect("chosen_pivot3")

    @View.nested
    class formatting(Tab):  # noqa
        page_size = BootstrapSelect("pdf_page_size")

    @View.nested
    class styling(Tab):  # noqa
        pass

    @View.nested
    class filter(Tab):  # noqa
        primary_filter = ExpressionEditor()
        secondary_filter = ExpressionEditor()

    @View.nested
    class summary(Tab):  # noqa
        sort_by = BootstrapSelect("chosen_sort1")
        sort_order = BootstrapSelect("sort_order")
        show_breaks = BootstrapSelect("sort_group")
        sort_by_2 = BootstrapSelect("chosen_sort2")
        row_limit = BootstrapSelect("row_limit")

    @View.nested
    class charts(Tab):  # noqa
        chart_type = BootstrapSelect("chosen_graph")
        chart_mode = BootstrapSelect("chart_mode")
        values_to_show = BootstrapSelect("chosen_count")
        sum_other_values = Checkbox("chosen_other")

    @View.nested
    class timeline(Tab):  # noqa
        based_on = BootstrapSelect("chosen_tl")
        position = BootstrapSelect("chosen_position")

    cancel_button = Button("Cancel")


class NewCustomReportView(CustomReportFormCommon):
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.report_title.text == "Adding a new Report" and
            self.reports.tree.currently_selected == ["All Reports"]
        )


class EditCustomReportView(CustomReportFormCommon):
    save_button = Button("Save")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.reports.tree.currently_selected == [
                "All Reports",
                "My Company (All EVM Groups)",
                "Custom",
                self.context["object"].menu_name
            ] and
            self.report_title.text == 'Editing Report "{}"'.format(self.context["object"].menu_name)
        )


class CustomReportDetailsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    reload_button = Button(title="Reload current display")

    @View.nested
    class report_info(Tab):
        queue_button = Button("Queue")
        TAB_NAME = "Report Info"

    @View.nested
    class saved_reports(Tab):
        TAB_NAME = "Saved Reports"
        table = Table(".//div[@id='records_div']/table")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.reports.tree.currently_selected == [
                "All Reports",
                "My Company (All EVM Groups)",
                "Custom",
                self.context["object"].menu_name
            ] and
            self.title.text == 'Report "{}"'.format(self.context["object"].menu_name)
        )


class AllReportsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.reports.tree.currently_selected == ["All Reports"] and
            self.title.text == "All Reports"
        )


class AllCustomReportsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.reports.tree.currently_selected == [
                "All Reports",
                "My Company (All EVM Groups)",
                "Custom"
            ] and
            self.title == "Custom Reports"
        )


class CustomReport(Updateable, Navigatable):
    _default_dict = {
        "menu_name": None,
        "title": None,
        "base_report_on": None,
        "report_fields": None,
        "cancel_after": None,
        "consolidation": None,
        "formatting": None,
        "styling": None,
        "filter": None,
        "summary": None,
        "charts": None,
        "timeline": None
    }

    def __init__(self, appliance=None, **values):
        Navigatable.__init__(self, appliance=appliance)
        # We will override the
        #  original dict
        self.__dict__ = dict(self._default_dict)
        self.__dict__.update(values)
        # We need to pass the knowledge whether it is a candu report
        try:
            self.is_candu
        except AttributeError:
            self.is_candu = False

    def create(self, cancel=False):
        view = navigate_to(self, "Add")
        view.fill(self.__dict__)
        view.add_button.click()
        view = self.create_view(AllReportsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_message('Report "{}" was added'.format("testing report"))

    def update(self, updates):
        view = navigate_to(self, "Edit")
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        for attr, value in updates.items():
            setattr(self, attr, value)
        view = self.create_view(CustomReportDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Report "{}" was saved'.format("testing report"))
        else:
            view.flash.assert_message(
                'Edit of Report "{}" was cancelled by the user'.format(self.menu_name))

    def delete(self, cancel=False):
        view = navigate_to(self, "Details")
        view.configuration.item_select("Delete this Report from the Database",
            handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            # This check needs because after deleting the last custom report
            # whole "My Company (All EVM Groups)" branch in the tree will be removed
            if len(get_all_custom_reports()) > 1:
                view = self.create_view(AllCustomReportsView)
                assert view.is_displayed
            view.flash.assert_no_error()
            view.flash.assert_message(
                'Report "{}": Delete successful'.format("testing report"))

    def get_saved_reports(self):
        pass

    def queue(self, wait_for_finish=False):
        view = navigate_to(self, "Details")
        view.report_info.queue_button.click()
        view.flash.assert_no_error()
        if wait_for_finish:
            # Get the queued_at value to always target the correct row
            queued_at = view.saved_reports.table[0]["Queued At"].text

            def _get_state():
                row = view.saved_reports.table.row(queued_at=queued_at)
                status = row.status.text.strip().lower()
                assert status != "error"
                return status == version.pick({
                    "5.6": "finished",
                    "5.7": "complete"
                })

            wait_for(
                _get_state,
                delay=1,
                message="wait for report generation finished",
                fail_func=view.reload_button.click,
                num_sec=300,
            )


def get_all_custom_reports():
    appliance = get_or_create_current_appliance()
    view = CloudIntelReportsView(appliance.browser.widgetastic)
    node = view.reports.tree.expand_path([
        "All Reports",
        "My Company (All EVM Groups)",
        "Custom"
    ])
    return view.reports.tree.child_items(node)


class CustomSavedReport(Updateable, Pretty, Navigatable):
    """Custom Saved Report. Enables us to retrieve data from the table.

    Args:
        report: Report that we have data from.
        datetime: Datetime of "Run At" of the report. That's what :py:func:`queue_canned_report`
            returns.
        candu: If it is a C&U report, in that case it uses a different table.
    """

    @cached_property
    def data(self):
        """Retrieves data from the saved report.

        Returns: :py:class:`SavedReportData` if it is not a candu report. If it is, then it returns
            a list of groups in the table.
        """
        pass

    def download(self, extension):
        pass


class CannedSavedReport(CustomSavedReport, Navigatable):
    """As we cannot create or edit canned reports, we don't know their titles and so, so we
    need to change the navigation a little bit for it to work correctly.

    Args:
        path_to_report: Iterable with path to report.
        datetime: Datetime of "Run At" of the report. That's what :py:func:`queue_canned_report`
            returns.
    """

    def __init__(self, path_to_report, datetime, candu=False, appliance=None):
        Navigatable.__init__(self, appliance=appliance)

    def navigate(self):
        pass

    @classmethod
    def new(cls, path):
        pass

    @classmethod
    def queue_canned_report(cls, path):
        pass

    def get_saved_canned_reports(self, *path):
        pass

    def delete(self):
        pass


@navigator.register(CustomReport, "Add")
class CustomReportNew(CFMENavigateStep):
    VIEW = NewCustomReportView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.view.reports.tree.click_path("All Reports")
        self.view.configuration.item_select("Add a new Report")


@navigator.register(CustomReport, "Edit")
class CustomReportEdit(CFMENavigateStep):
    VIEW = EditCustomReportView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.view.configuration.item_select("Edit this Report")


@navigator.register(CustomReport, "Details")
class CustomReportDetails(CFMENavigateStep):
    VIEW = CustomReportDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.view.reports.tree.click_path(
            "All Reports",
            "My Company (All EVM Groups)",
            "Custom",
            self.obj.menu_name
        )
