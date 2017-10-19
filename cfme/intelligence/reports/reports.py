# -*- coding: utf-8 -*-
"""Page model for Cloud Intel / Reports / Reports"""
from cached_property import cached_property
from navmazing import NavigateToAttribute, NavigateToSibling
from cfme.utils.wait import wait_for
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.timeutil import parsetime
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from . import CloudIntelReportsView, ReportsMultiBoxSelect

from widgetastic.utils import ParametrizedLocator
from widgetastic.widget import Text, Checkbox, View, ParametrizedView, Table as VanillaTable
from widgetastic.exceptions import NoSuchElementException
from widgetastic_manageiq import PaginationPane, Table
from widgetastic_patternfly import Button, Input, BootstrapSelect, Tab, CandidateNotFound
from cfme.web_ui.expression_editor_widgetastic import ExpressionEditor


class CustomReportFormCommon(CloudIntelReportsView):
    report_title = Text("#explorer_title_text")

    menu_name = Input("name")
    title = Input("title")
    base_report_on = BootstrapSelect("chosen_model")
    report_fields = ReportsMultiBoxSelect(
        move_into="Move selected fields down",
        move_from="Move selected fields up",
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
        filter_show_costs = BootstrapSelect("cb_show_typ")
        filter_owner = BootstrapSelect("cb_owner_id")
        filter_provider = BootstrapSelect("cb_provider_id")
        filter_project = BootstrapSelect("cb_entity_id")
        filter_tag_cat = BootstrapSelect("cb_tag_cat")
        filter_tag_value = BootstrapSelect("cb_tag_value")
        interval = BootstrapSelect("cb_interval")
        interval_size = BootstrapSelect("cb_interval_size")
        interval_end = BootstrapSelect("cb_end_interval_offset")
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
    paginator = PaginationPane()

    @View.nested
    class report_info(Tab):  # noqa
        TAB_NAME = "Report Info"
        queue_button = Button("Queue")

    @View.nested
    class saved_reports(Tab):  # noqa
        TAB_NAME = "Saved Reports"
        table = Table(".//div[@id='records_div']/table")
        paginator = PaginationPane()

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.report_info.is_active() and
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
    reports_table = VanillaTable(".//div[@id='report_list_div']/table")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.reports.tree.currently_selected == ["All Reports"] and
            self.title.text == "All Reports" and
            self.reports_table.is_displayed
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
            self.title.text == "Custom Reports"
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
        "filter_show_costs": None,
        "filter_owner": None,
        "filter_tag_cat": None,
        "filter_tag_value": None,
        "interval": None,
        "interval_size": None,
        "interval_end": None,
        "sort": None,
        "chart_type": None,
        "top_values": None,
        "sum_other": None,
        "base_timeline_on": None,
        "band_units": None,
        "event_position": None,
        "show_event_unit": None,
        "show_event_count": None,
        "summary": None,
        "charts": None,
        "timeline": None
    }

    def __init__(self, appliance=None, **values):
        Navigatable.__init__(self, appliance=appliance)
        # We will override the original dict
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
        view.flash.assert_message('Report "{}" was added'.format(self.menu_name))

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
                'Report "{}" was saved'.format(self.menu_name))
        else:
            view.flash.assert_message(
                'Edit of Report "{}" was cancelled by the user'.format(self.menu_name))

    def delete(self, cancel=False):
        view = navigate_to(self, "Details")
        node = view.reports.tree.expand_path("All Reports", "My Company (All EVM Groups)", "Custom")
        custom_reports_number = len(view.reports.tree.child_items(node))
        view.configuration.item_select("Delete this Report from the Database",
            handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            # This check needs because after deleting the last custom report
            # whole "My Company (All EVM Groups)" branch in the tree will be removed.
            if custom_reports_number > 1:
                view = self.create_view(AllCustomReportsView)
                assert view.is_displayed
            view.flash.assert_no_error()
            view.flash.assert_message(
                'Report "{}": Delete successful'.format(self.menu_name))

    def get_saved_reports(self):
        view = navigate_to(self, "Details")
        results = []
        try:
            for _ in view.saved_reports.paginator.pages():
                for row in view.saved_reports.table.rows():
                    results.append(
                        CustomSavedReport(self, row.run_at.text.encode("utf-8"),
                            row.queued_at.text.encode("utf-8"), self.is_candu)
                    )
        except NoSuchElementException:
            pass
        return results

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
                return status == "complete"

            wait_for(
                _get_state,
                delay=1,
                message="wait for report generation finished",
                fail_func=view.reload_button.click,
                num_sec=300,
            )


class CustomSavedReportDetailsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    table = VanillaTable(".//div[@id='report_html_div']/table")
    paginator = PaginationPane()

    @ParametrizedView.nested
    class download(ParametrizedView):  # noqa
        PARAMETERS = ("format", )
        ALL_LINKS = ".//a[starts-with(@name, 'download_choice__render_report_')]"
        download_button = Button(title="Download")
        link = Text(ParametrizedLocator(".//a[normalize-space()={format|quote}]"))

        def __init__(self, *args, **kwargs):
            ParametrizedView.__init__(self, *args, **kwargs)
            self.download_button.click()
            self.link.click()

        @classmethod
        def all(cls, browser):
            return [(browser.text(e), ) for e in browser.elements(cls.ALL_LINKS)]

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.reports.tree.currently_selected == [
                "All Reports",
                "My Company (All EVM Groups)",
                "Custom",
                self.context["object"].report.menu_name,
                self.context["object"].datetime_in_tree
            ] and
            self.title.text == 'Saved Report "{} - {}"'.format(
                self.context["object"].report.title,
                self.context["object"].queued_datetime_in_title
            )
        )


class CustomSavedReport(Updateable, Pretty, Navigatable):
    """Custom Saved Report. Enables us to retrieve data from the table.

    Args:
        report: Report that we have data from.
        run_datetime: Datetime of "Run At" of the report. That's what :py:func:`queue` returns.
        queued_datetime: Datetime of "Queued At" of the report.
        candu: If it is a C&U report, in that case it uses a different table.
    """

    pretty_attrs = ["report", "run_datetime", "queued_datetime"]

    def __init__(self, report, run_datetime, queued_datetime, candu=False, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.report = report
        self.run_datetime = run_datetime
        self.queued_datetime_in_title = parsetime.from_american_with_utc(
            queued_datetime).to_saved_report_title_format()
        self.datetime_in_tree = parsetime.from_american_with_utc(
            self.run_datetime).to_iso_with_utc()
        self.candu = candu

    @cached_property
    def data(self):
        """Retrieves data from the saved report.

        Returns: :py:class:`SavedReportData`.
        """
        view = navigate_to(self, "Details")
        if 'No records found for this report' in view.flash.read():
            # No data found
            return SavedReportData([], [])
        view.paginator.set_items_per_page(1000)
        try:
            headers = tuple([hdr.encode("utf-8") for hdr in view.table.headers])
            body = []
            for _ in view.paginator.pages():
                for row in view.table.rows():
                    if not all([c[1].is_displayed for c in row]):
                        # This is a temporary workaround for cases we have row span
                        # greater that 1 column (e.g. in case of "Totals: ddd" column).
                        # TODO: Support this functionality in widgetastic. Issue:
                        # https://github.com/RedHatQE/widgetastic.core/issues/26
                        continue
                    row_data = tuple([row[header].text.encode("utf-8") for header in headers])
                    body.append(row_data)
        except NoSuchElementException:
            # No data found
            return SavedReportData([], [])
        else:
            return SavedReportData(headers, body)

    def download(self, extension):
        view = navigate_to(self, "Details")
        extensions_mapping = {"txt": "Text", "csv": "CSV", "pdf": "PDF"}
        try:
            view.download("Download as {}".format(extensions_mapping[extension]))
        except NoSuchElementException:
            raise ValueError("Unknown extention. check the extentions_mapping")


class SavedReportData(Pretty):
    """This class stores data retrieved from saved report.

    Args:
        headers: Tuple with header columns.
        body: List of tuples with body rows.
    """
    pretty_attrs = ["headers", "body"]

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


class CannedReportView(CustomReportDetailsView):

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.report_info.is_active() and
            self.reports.tree.currently_selected == (["All Reports"] +
                self.context["object"].path) and
            self.title.text == 'Report "{}"'.format(self.context["object"].path[-1])
        )


class CannedSavedReportView(CustomSavedReportDetailsView):

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.reports.tree.currently_selected == (
                ["All Reports"] + self.context["object"].path
            ) and
            self.title.text == 'Saved Report "{} - {}"'.format(
                self.context["object"].path[-1],
                self.context["object"].queued_datetime_in_title
            )
        )


class CannedSavedReport(CustomSavedReport, Navigatable):
    """As we cannot create or edit canned reports, we don't know their titles and so, so we
    need to change the navigation a little bit for it to work correctly.

    Args:
        path_to_report: Iterable with path to report.
        datetime: Datetime of "Run At" of the report. That's what :py:func:`queue_canned_report`
            returns.
    """

    def __init__(self, path_to_report, run_datetime, queued_datetime, candu=False, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.path = path_to_report
        self.datetime = run_datetime
        self.candu = candu
        self.queued_datetime_in_title = parsetime.from_american_with_utc(
            queued_datetime).to_saved_report_title_format()
        self.datetime_in_tree = parsetime.from_american_with_utc(self.datetime).to_iso_with_utc()

    def navigate(self):
        navigate_to(self, "Details")

    @classmethod
    def new(cls, path):
        return cls(path, *cls.queue_canned_report(path))

    @classmethod
    def queue_canned_report(cls, path):
        """Queue report from selection of pre-prepared reports.

        Args:
            *path: Path in tree after All Reports
        Returns: Value of Run At in the table so the run can be then checked.
        """
        cls.path = path
        view = navigate_to(cls, "Info")
        assert view.is_displayed
        view.report_info.queue_button.click()
        view.flash.assert_no_error()
        view.flash.assert_message("Report has been successfully queued to run")
        queued_at = view.saved_reports.table[0]["Queued At"].text

        def _get_state():
            row = view.saved_reports.table.row(queued_at=queued_at)
            status = row.status.text.strip().lower()
            assert status != "error"
            return status == "complete"

        wait_for(
            _get_state,
            delay=1,
            message="wait for report generation finished",
            fail_func=view.reload_button.click,
            num_sec=300,
        )
        first_row = view.saved_reports.table[0]
        return first_row.run_at.text, first_row.queued_at.text

    def get_saved_canned_reports(self, *path):
        view = navigate_to(self, "Info")
        results = []
        try:
            for _ in view.saved_reports.paginator.pages():
                for row in view.saved_reports.table.rows():
                    if not all([c[1].is_displayed for c in row]):
                        # This is a temporary workaround for cases we have row span
                        # greater that 1 column (e.g. in case of "Totals: ddd" column).
                        # TODO: Support this functionality in widgetastic. Issue:
                        # https://github.com/RedHatQE/widgetastic.core/issues/26
                        continue
                    results.append(
                        CannedSavedReport(
                            path,
                            row.run_at.text.encode("utf-8"),
                            row.queued_at.text.encode("utf-8")
                        )
                    )
        except NoSuchElementException:
            pass
        return results

    def delete(self, cancel=False):
        view = navigate_to(self, "Info")
        cell = view.saved_reports.table.row(run_at=self.datetime)[0]
        cell.check()
        view.configuration.item_select(
            "Delete this Saved Report from the Database",
            handle_alert=not cancel
        )
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view.flash.assert_no_error()
            # TODO Doesn't work due to this BZ https://bugzilla.redhat.com/show_bug.cgi?id=1489387
            # view.flash.assert_message("Successfully deleted Saved Report from the CFME Database")

    @property
    def exists(self):
        try:
            navigate_to(self, 'Info')
            return True
        except CandidateNotFound:
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()


@navigator.register(CustomReport, "Add")
class CustomReportNew(CFMENavigateStep):
    VIEW = NewCustomReportView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.prerequisite_view.reports.tree.click_path("All Reports")
        self.prerequisite_view.configuration.item_select("Add a new Report")


@navigator.register(CustomReport, "Edit")
class CustomReportEdit(CFMENavigateStep):
    VIEW = EditCustomReportView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.configuration.item_select("Edit this Report")


@navigator.register(CustomReport, "Details")
class CustomReportDetails(CFMENavigateStep):
    VIEW = CustomReportDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.prerequisite_view.reports.tree.click_path(
            "All Reports",
            "My Company (All EVM Groups)",
            "Custom",
            self.obj.menu_name
        )
        self.view.report_info.select()


@navigator.register(CustomSavedReport, "Details")
class CustomSavedReportDetails(CFMENavigateStep):
    VIEW = CustomSavedReportDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.prerequisite_view.reports.tree.click_path(
            "All Reports",
            "My Company (All EVM Groups)",
            "Custom",
            self.obj.report.menu_name,
            self.obj.datetime_in_tree
        )


@navigator.register(CannedSavedReport, "Details")
class CannedSavedReportDetails(CFMENavigateStep):
    VIEW = CannedSavedReportView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        path = self.obj.path + [self.obj.datetime_in_tree]
        self.prerequisite_view.reports.tree.click_path("All Reports", *path)


@navigator.register(CannedSavedReport, "Info")
class CannedReportInfo(CFMENavigateStep):
    VIEW = CannedReportView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.prerequisite_view.reports.tree.click_path("All Reports", *self.obj.path)


@navigator.register(CustomReport, "All")
class CustomReportAll(CFMENavigateStep):
    VIEW = AllReportsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.prerequisite_view.reports.tree.click_path("All Reports")
