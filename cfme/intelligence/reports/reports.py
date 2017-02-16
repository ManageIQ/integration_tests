# -*- coding: utf-8 -*-
"""Page model for Cloud Intel / Reports / Reports"""
from cached_property import cached_property
from utils.pretty import Pretty
<<<<<<< HEAD
from cfme.exceptions import ItemNotFound
=======
from utils.update import Updateable
>>>>>>> Cloud Intel / Reports / Reports conversion to widgetastic
from utils.appliance import Navigatable
from navmazing import NavigateToAttribute
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from . import CloudIntelReportsView

from widgetastic.widget import Text, Checkbox, View
from widgetastic_manageiq import SummaryFormItem, DashboardWidgetsPicker, MultiBoxSelect
from widgetastic_patternfly import Button, Input, BootstrapSelect, Tab
from cfme.web_ui.expression_editor_widgetastic import ExpressionEditor


class CustomReportFormCommon(CloudIntelReportsView):
    title = Text("#explorer_title_text")

    name = Input("name")
    title = Input("title")

    @View.nested
    class columns(Tab):  # noqa
        based_on = BootstrapSelect("chosen_model")
        fields = MultiBoxSelect(
            "column_lists",
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
            self.title.text == "Adding a new Report"
        )


class EditCustomReportView(CustomReportFormCommon):
    save_button = Button("Save")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == 'Editing Report "{}"'.format(self.context["object"].name)
        )


class CustomReport(Updateable, Navigatable):

    def __init__(self, appliance=None, **values):
        Navigatable.__init__(self, appliance=appliance)

    def create(self, cancel=False):
        view = navigate_to(self, "Add")
        view.fill({
        })
        view.add_button.click()
        view = self.create_view(AllReportsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_message('Report "{}" was added'.format(self.description))

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
                'Report "{}" was saved'.format(
                    updates.get("description", self.description)))
        else:
            view.flash.assert_message(
                'Edit of Report "{}" was cancelled by the user'.format(self.description))

    def delete(self, cancel=False):
        view = navigate_to(self, "Details")
        view.configuration.item_select("Delete this Report from the Database",
            handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view = self.create_view(AllCustomReportsView)
            assert view.is_displayed
            view.flash.assert_no_error()
            view.flash.assert_message(
                'Report "{}": Delete successful'.format(self.description))

    def get_saved_reports(self):
        pass

    def queue(self, wait_for_finish=False):
        pass


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
<<<<<<< HEAD
        navigate_to(self, 'Saved')
        self.saved_table.select_row(header='Run At', value=self.datetime)
        cfg_btn("Delete this Saved Report from the Database", invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()

    @property
    def exists(self):
        try:
            navigate_to(self, 'Saved')
            return True
        except ItemNotFound:
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()


@navigator.register(CannedSavedReport, 'Details')
class CannedSavedDetails(CFMENavigateStep):
    prerequisite = NavigateToObject(CustomReport, 'All')

    def step(self):
        accordion.tree(
            "Reports", *(["All Reports"] + self.obj.path + [self.obj.datetime_in_tree]))


@navigator.register(CannedSavedReport, 'Path')
class CannedPath(CFMENavigateStep):
    prerequisite = NavigateToObject(CustomReport, 'All')

    def step(self):
        accordion.tree("Reports", *(["All Reports"] + self.obj.path))


@navigator.register(CannedSavedReport, 'Info')
class CannedInfo(CFMENavigateStep):
    prerequisite = NavigateToSibling('Path')

    def step(self):
        tabstrip.select_tab("Report Info")


@navigator.register(CannedSavedReport, 'Saved')
class CannedSave(CFMENavigateStep):
    prerequisite = NavigateToSibling('Path')

    def step(self):
        tabstrip.select_tab("Saved Reports")


class SavedReportData(Pretty):
    """This class stores data retrieved from saved report.

    Args:
        headers: Tuple with header columns.
        body: List of tuples with body rows.
    """
    pretty_attrs = ['headers', 'body']

    def __init__(self, headers, body):
        self.headers = headers
        self.body = body

    @property
    def rows(self):
        for row in self.body:
            yield dict(zip(self.headers, row))

    def find_row(self, column, value):
        if column not in self.headers:
            return None
        for row in self.rows:
            if row[column] == value:
                return row

    def find_cell(self, column, value, cell):
        try:
            return self.find_row(column, value)[cell]
        except TypeError:
            return None
=======
        pass
>>>>>>> Cloud Intel / Reports / Reports conversion to widgetastic
