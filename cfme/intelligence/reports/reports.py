"""Page model for Cloud Intel / Reports / Reports"""
import attr
from cached_property import cached_property
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import attributize_string
from widgetastic.widget import Checkbox
from widgetastic.widget import FileInput
from widgetastic.widget import Select
from widgetastic.widget import Table as VanillaTable
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import Input
from widgetastic_patternfly import SelectorDropdown

from cfme.exceptions import RestLookupError
from cfme.intelligence.reports import CloudIntelReportsView
from cfme.intelligence.reports import ReportsMultiBoxSelect
from cfme.intelligence.reports.schedules import SchedulesFormCommon
from cfme.intelligence.timelines import CloudIntelTimelinesView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils import ParamClassName
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.timeutil import parsetime
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for
from widgetastic_manageiq import InputButton
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import ReportToolBarViewSelector
from widgetastic_manageiq import SearchBox
from widgetastic_manageiq import SummaryFormItem
from widgetastic_manageiq import Table
from widgetastic_manageiq import WaitTab
from widgetastic_manageiq.expression_editor import ExpressionEditor


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
    class consolidation(WaitTab):  # noqa
        column1 = BootstrapSelect("chosen_pivot1")
        column2 = BootstrapSelect("chosen_pivot2")
        column3 = BootstrapSelect("chosen_pivot3")

    @View.nested
    class formatting(WaitTab):  # noqa
        page_size = BootstrapSelect("pdf_page_size")

    @View.nested
    class styling(WaitTab):  # noqa
        pass

    @View.nested
    class filter(WaitTab):  # noqa
        filter_show_costs = BootstrapSelect("cb_show_typ")
        filter_owner = BootstrapSelect("cb_owner_id")
        filter_provider = BootstrapSelect("cb_provider_id")
        filter_project = BootstrapSelect("cb_entity_id")
        filter_tag_cat = BootstrapSelect("cb_tag_cat")
        filter_tag_value = BootstrapSelect("cb_tag_value")
        interval = BootstrapSelect("cb_interval")
        interval_size = BootstrapSelect("cb_interval_size")
        interval_end = BootstrapSelect("cb_end_interval_offset")
        primary_record_filter = Button("contains", "Record Filter")
        secondary_display_filter = Button("contains", "Display Filter")

        @View.nested
        class primary_filter(ExpressionEditor):     # noqa
            def child_widget_accessed(self, widget):
                if self.parent.primary_record_filter.is_displayed:
                    self.parent.primary_record_filter.click()

        @View.nested
        class secondary_filter(ExpressionEditor):   # noqa
            def child_widget_accessed(self, widget):
                if self.parent.secondary_display_filter.is_displayed:
                    self.parent.secondary_display_filter.click()

    @View.nested
    class summary(WaitTab):  # noqa
        sort_by = BootstrapSelect("chosen_sort1")
        sort_order = BootstrapSelect("sort_order")
        show_breaks = BootstrapSelect("sort_group")
        sort_by_2 = BootstrapSelect("chosen_sort2")
        row_limit = BootstrapSelect("row_limit")

    @View.nested
    class charts(WaitTab):  # noqa
        chart_type = BootstrapSelect("chosen_graph")
        chart_mode = BootstrapSelect("chart_mode")
        values_to_show = BootstrapSelect("chosen_count")
        sum_other_values = Checkbox("chosen_other")

    @View.nested
    class timeline(WaitTab):  # noqa
        based_on = BootstrapSelect("chosen_tl")
        position = BootstrapSelect("chosen_position")

    cancel_button = Button("Cancel")


class ReportAddView(CustomReportFormCommon):
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.report_title.text == "Adding a new Report" and
            self.reports.tree.currently_selected == ["All Reports"]
        )


class ReportEditView(CustomReportFormCommon):
    save_button = Button("Save")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.reports.tree.currently_selected == self.context["object"].tree_path and
            self.report_title.text == 'Editing Report "{}"'.format(self.context["object"].menu_name)
        )


class ReportCopyView(ReportAddView):
    """ Class for copying a report, functionally this is the same as the ReportAddView.
    The is_displayed function needs to be slightly modified. """

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.report_title.text == "Adding a new Report" and
            self.reports.tree.currently_selected == self.context["object"].tree_path
        )


class ReportDetailsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    reload_button = Button(title='Refresh this page')
    paginator = PaginationPane()

    @View.nested
    class report_info(WaitTab):  # noqa
        TAB_NAME = "Report Info"
        # Keeping `group_title` empty since the summary form has no title
        report_id = SummaryFormItem("", "ID")
        title = SummaryFormItem("", "Title")
        primary_filter = SummaryFormItem("", "Primary (Record) Filter")
        secondary_filter = SummaryFormItem("", "Secondary (Display) Filter")
        sort_by = SummaryFormItem("", "Sort By")
        based_on = SummaryFormItem("", "Based On")
        user = SummaryFormItem("", "User")
        group = SummaryFormItem("", "EVM Group")
        updated_on = SummaryFormItem("", "Updated On")
        # xpath is defined based on the value of the second title head of table
        report_schedule_data = Table(
            '//*[@id="report_info"]//th[contains(text(), "Name")]'
            '/parent::tr/parent::thead/parent::table'
        )
        report_widgets_data = Table(
            '//*[@id="report_info"]//th[contains(text(), "Title")]'
            '/parent::tr/parent::thead/parent::table'
        )
        queue_button = Button("Queue")

    @View.nested
    class saved_reports(WaitTab):  # noqa
        TAB_NAME = "Saved Reports"
        table = Table(".//div[@id='records_div' or @class='miq-data-table']/table")
        paginator = PaginationPane()

    @property
    def is_displayed(self):
        expected_title = 'Report "{}"'.format(self.context["object"].menu_name)
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.report_info.is_displayed and
            self.reports.tree.currently_selected == self.context["object"].tree_path and
            self.title.text == expected_title
        )


class ReportTimelineView(CloudIntelTimelinesView):
    title = Text(".//h1")

    @property
    def is_displayed(self):
        # Skipping the first element of report object's tree_path in Timelines,
        # since Timeline doesn't include `All Reports` in it's tree_path,
        # which is why tree.currently_selected is checked against tree_path[1:]
        return (
            self.logged_in_as_current_user
            and self.navigation.currently_selected == ['Overview', 'Timelines']
            and self.timelines.tree.currently_selected == self.context["object"].tree_path[1:]
        )


class SavedReportDetailsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    table = VanillaTable(".//div[@id='report_html_div']/table")
    # PaginationPane() is not working on Report Details page
    # TODO: double check and raise GH to devs
    paginator = PaginationPane()
    view_selector = View.nested(ReportToolBarViewSelector)
    download = Dropdown("Download")

    @View.nested
    class data_view(View):  # noqa
        table = Table('//*[@id="report_list_div"]//table')
        field = SelectorDropdown("id", "filterFieldTypeMenu")
        search_text = SearchBox(locator='//input[contains(@placeholder, "search text")]')

        # TODO: Write a separate paginator for data view
        def child_widget_accessed(self, widget):
            if self.parent.view_selector.selected != "Data View":
                self.parent.view_selector.select("Data View")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports
            and self.reports.is_opened
            and self.reports.tree.currently_selected == self.context["object"].tree_path
            and self.context["object"].queued_datetime_in_title in self.title.text
            and self.breadcrumb.locations
            == ["Overview", "Reports", "Reports", self.context["object"].datetime_in_tree]
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
        # This view is only used when more than one custom reports are present and
        # one of them is deleted. It is used to check if the tree_path
        # [`All Reports`, `My Company (All Groups)`, `Custom`] is available even after
        # one of the custom reports has been deleted, which is why
        # tree.currently_selected is checked against tree_path[:3]
        return (
            self.in_intel_reports and
            self.reports.is_opened and
            self.reports.tree.currently_selected == self.context["object"].tree_path[:3] and
            self.title.text == "Custom Reports"
        )


class ReportScheduleView(SchedulesFormCommon):
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports
            and self.title.text == "Adding a new Schedule"
            and self.reports.tree.currently_selected == self.context["object"].tree_path
        )


class ImportExportCustomReportsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    subtitle = Text(locator=".//div[@id='main_div']/h2")

    upload_file = FileInput(id="upload_file")
    upload_button = InputButton("commit")

    overwrite = Checkbox("overwrite")
    preserve_owner = Checkbox("preserve_owner")

    items_for_export = Select(id="choices_chosen")
    export_button = Button(id="export_button")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports
            and self.title.text == "Import / Export"
            and self.subtitle.text == "Custom Reports"
            and self.import_export.tree.currently_selected
            == ["Import / Export", "Custom Reports"]
        )


@attr.s
class Report(BaseEntity, Updateable):
    _param_name = ParamClassName('title')
    menu_name = attr.ib(default=None)
    title = attr.ib(default=None)
    company_name = attr.ib()
    type = attr.ib(default=None)
    subtype = attr.ib(default=None)
    base_report_on = attr.ib(default=None)
    report_fields = attr.ib(default=None)
    cancel_after = attr.ib(default=None)
    consolidation = attr.ib(default=None)
    formatting = attr.ib(default=None)
    styling = attr.ib(default=None)
    filter = attr.ib(default=None)
    filter_show_costs = attr.ib(default=None)
    filter_owner = attr.ib(default=None)
    filter_tag_cat = attr.ib(default=None)
    filter_tag_value = attr.ib(default=None)
    interval = attr.ib(default=None)
    interval_size = attr.ib(default=None)
    interval_end = attr.ib(default=None)
    sort = attr.ib(default=None)
    chart_type = attr.ib(default=None)
    top_values = attr.ib(default=None)
    sum_other = attr.ib(default=None)
    base_timeline_on = attr.ib(default=None)
    band_units = attr.ib(default=None)
    event_position = attr.ib(default=None)
    show_event_unit = attr.ib(default=None)
    show_event_count = attr.ib(default=None)
    summary = attr.ib(default=None)
    charts = attr.ib(default=None)
    timeline = attr.ib(default=None)
    is_candu = attr.ib(default=False)

    def __attrs_post_init__(self):
        self._collections = {'saved_reports': SavedReportsCollection}

    @company_name.default
    def company_name_default(self):
        return "My Company (All Groups)"

    def update(self, updates):
        view = navigate_to(self, "Edit")
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(ReportDetailsView, override=updates, wait='10s')
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                f'Report "{self.menu_name}" was saved')
        else:
            view.flash.assert_message(
                f'Edit of Report "{self.menu_name}" was cancelled by the user')

    def copy(self):
        """ Copy a report via UI and return a copy of a Report object"""
        menu_name = f"Copy of {self.menu_name}"

        view = navigate_to(self, "Copy")
        view.add_button.click()
        self.create_view(AllReportsView, wait="5s")

        return self.appliance.collections.reports.instantiate(
            type=self.company_name, subtype="Custom", menu_name=menu_name, title=self.title,
        )

    def delete(self, cancel=False):
        view = navigate_to(self, "Details")
        node = view.reports.tree.expand_path("All Reports", self.company_name, "Custom")
        custom_reports_number = len(view.reports.tree.child_items(node))
        view.configuration.item_select("Delete this Report from the Database",
                                       handle_alert=not cancel)
        if cancel:
            view.wait_displayed()
            view.flash.assert_no_error()
        else:
            # This check is needed because after deleting the last custom report,
            # the whole "My Company (All EVM Groups)" branch in the tree will be removed.
            if custom_reports_number > 1:
                view = self.create_view(AllCustomReportsView, wait='5s')
            view.flash.assert_no_error()
            view.flash.assert_message(f'Report "{self.menu_name}": Delete successful')

    @cached_property
    def saved_reports(self):
        return self.collections.saved_reports

    def create_schedule(
        self,
        name=None,
        description=None,
        active=True,
        timer=None,
        email=None,
        email_options=None,
        cancel=False,
    ):
        view = navigate_to(self, "ScheduleReport")
        if email:
            email["emails_send"] = True
        schedule = self.appliance.collections.schedules.instantiate(
            name=name or self.menu_name,
            description=description or self.menu_name,
            active=active,
            report_filter={
                "filter_type": self.company_name,
                "subfilter_type": self.subtype,
                "report_type": self.menu_name,
            },
            timer=timer,
            email=email,
            email_options=email_options
        )
        view.fill(schedule.fill_dict)

        if cancel:
            view.cancel_button.click()
        else:
            view.add_button.click()
        view.flash.assert_no_error()

        assert schedule.exists
        return schedule

    def queue(self, wait_for_finish=False):
        view = navigate_to(self, "Details")
        view.report_info.queue_button.click()
        view.flash.assert_no_error()
        if wait_for_finish:
            # Get the queued_at value to always target the correct row
            if view.saved_reports.paginator.sorted_by['sortDir'] != "DESC":
                view.saved_reports.paginator.sort(sort_by="Queued At", ascending=False)
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
            view.reload_button.click()
        first_row = view.saved_reports.table[0]
        saved_report = self.saved_reports.instantiate(
            first_row.run_at.text,
            first_row.queued_at.text,
            self.is_candu
        )
        return saved_report

    @property
    def tree_path(self):
        return [
            "All Reports",
            self.type or self.company_name,
            self.subtype or "Custom",
            self.menu_name,
        ]

    @property
    def rest_api_entity(self):
        try:
            return self.appliance.rest_api.collections.reports.get(name=self.menu_name)
        except ValueError:
            raise RestLookupError(
                f"No report rest entity found matching name {self.menu_name}"
            )


@attr.s
class ReportsCollection(BaseCollection):
    ENTITY = Report

    def create(self, **values):
        view = navigate_to(self, "Add")
        view.fill(values)
        view.add_button.click()
        view = self.create_view(AllReportsView, wait='5s')
        view.flash.assert_no_error()
        view.flash.assert_message('Report "{}" was added'.format(values["menu_name"]))
        return self.instantiate(**values)

    def import_report(
        self, filepath, preserve_owner=False, overwrite=False
    ):
        """
        Import yaml files containing report data
        Args:
            filepath (str): Complete path to the file
            preserve_owner (bool): If true, original owner of the report will be preserved
            overwrite (bool): If true, a possible duplicate of the report will be overwritten
        """
        view = navigate_to(self, "ImportExport")

        view.fill(
            {
                "upload_file": filepath,
                "preserve_owner": preserve_owner,
                "overwrite": overwrite,
            }
        )
        view.upload_button.click()
        view.flash.assert_no_error()

    def export_report(self, *reports):
        """
        Export custom report
        Args:
            reports (str, tuple): name of reports to be exported
        """
        view = navigate_to(self, "ImportExport")

        view.items_for_export.fill(*reports)
        view.export_button.click()
        view.flash.assert_no_error()


@attr.s
class SavedReport(Updateable, BaseEntity):
    """Custom Saved Report. Enables us to retrieve data from the table.

    Args:
        run_datetime: Datetime of "Run At" of the report. That's what :py:func:`queue` returns.
        queued_datetime: Datetime of "Queued At" of the report.
        candu: If it is a C&U report, in that case it uses a different table.
    """

    run_datetime = attr.ib()
    queued_datetime = attr.ib()
    candu = attr.ib(default=False)

    @property
    def parent_obj(self):
        return self.parent.parent

    @property
    def report(self):
        return self.parent_obj

    @property
    def report_timezone(self):
        return self.queued_datetime.split()[-1]

    @cached_property
    def queued_datetime_in_title(self):
        # when the timezone is changed,
        # "display" key will not be available without clearing the cache
        delattr(self.appliance, "rest_api")
        try:
            area = self.appliance.rest_api.settings["display"]["timezone"]
        except KeyError:
            area = "UTC"
        return parsetime.from_american(
            self.queued_datetime, self.report_timezone
        ).to_saved_report_title_format(area)

    @cached_property
    def datetime_in_tree(self):
        return parsetime.from_american(
            self.run_datetime, self.report_timezone
        ).to_iso(self.report_timezone)

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
            headers = tuple([hdr for hdr in view.table.headers])
            body = []
            for _ in range(view.paginator.pages_amount):
                for row in view.table.rows():
                    if not all([c[1].is_displayed for c in row]):
                        # This is a temporary workaround for cases we have row span
                        # greater that 1 column (e.g. in case of "Totals: ddd" column).
                        # TODO: Support this functionality in widgetastic. Issue:
                        # https://github.com/RedHatQE/widgetastic.core/issues/26
                        continue
                    row_data = tuple([row[header].text for header in headers])
                    body.append(row_data)
        except NoSuchElementException:
            # No data found
            return SavedReportData([], [])
        else:
            return SavedReportData(headers, body)

    def download(self, extension):
        extensions_mapping = {"txt": "Text", "csv": "CSV", "pdf": "PDF"}
        if extension == "pdf":
            logger.info("PDF download is not implemented because of multiple window handling.")
        view = navigate_to(self, "Details")
        view.download.item_select(f"Download as {extensions_mapping[extension]}")

    def delete(self, cancel=False):
        view = navigate_to(self, "Details")
        view.configuration.item_select(
            "Delete this Saved Report from the Database",
            handle_alert=not cancel
        )
        view.flash.assert_no_error()
        if cancel:
            assert view.is_displayed
        else:
            view.flash.assert_message("Successfully deleted Saved Report from the CFME Database")

    @property
    def tree_path(self):
        return self.report.tree_path + [self.datetime_in_tree]

    def filter_report_content(self, field, search_term):
        view = navigate_to(self, "Details")
        # TODO: Add a working paginator for the data view
        # view.data_view.paginator.set_items_per_page(1000)
        view.data_view.field.item_select(field)
        view.data_view.search_text.fill(search_term, refill=True)
        return view.data_view.table

    def sort_column(self, field, order="asc"):
        field = attributize_string(field)
        view = navigate_to(self, "Details")
        view.data_view.table.sort_by(field, order=order)
        assert view.data_view.table.sorted_by == field
        assert view.data_view.table.sort_order == order


@attr.s
class SavedReportsCollection(BaseCollection):
    ENTITY = SavedReport

    def all(self):
        view = navigate_to(self.parent, "Details")
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
                        self.instantiate(
                            row.run_at.text,
                            row.queued_at.text,
                            self.parent.is_candu
                        )
                    )
        except NoSuchElementException:
            pass
        return results


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


@navigator.register(ReportsCollection, "All")
class ReportsAll(CFMENavigateStep):
    VIEW = AllReportsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self, *args, **kwargs):
        self.prerequisite_view.reports.tree.click_path("All Reports")


@navigator.register(ReportsCollection, "Add")
class ReportsNew(CFMENavigateStep):
    VIEW = ReportAddView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self, *args, **kwargs):
        self.prerequisite_view.reports.tree.click_path("All Reports")
        self.prerequisite_view.configuration.item_select("Add a new Report")


@navigator.register(Report, "Edit")
class ReportEdit(CFMENavigateStep):
    VIEW = ReportEditView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Edit this Report")


@navigator.register(Report, "Copy")
class ReportCopy(CFMENavigateStep):
    VIEW = ReportCopyView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Copy this Report")


@navigator.register(Report, "Timeline")
class ReportTimeline(CFMENavigateStep):
    VIEW = ReportTimelineView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelTimelines")

    def step(self, *args, **kwargs):
        # Skipping the first element of report object's tree_path in Timelines,
        # since Timeline doesn't include `All Reports` in it's tree_path,
        # which is why tree.currently_selected is checked against tree_path[1:]
        self.prerequisite_view.timelines.tree.click_path(*self.obj.tree_path[1:])


@navigator.register(Report, "Details")
class ReportDetails(CFMENavigateStep):
    VIEW = ReportDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.reports.tree.click_path(*self.obj.tree_path)
        self.view.report_info.select()


@navigator.register(Report, "ScheduleReport")
class ReportSchedule(CFMENavigateStep):
    VIEW = ReportScheduleView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self, *args, **kwargs):
        self.prerequisite_view.reports.tree.click_path(*self.obj.tree_path)
        self.prerequisite_view.configuration.item_select("Add a new Schedule")


@navigator.register(SavedReport, "Details")
class SavedReportDetails(CFMENavigateStep):
    VIEW = SavedReportDetailsView
    prerequisite = NavigateToAttribute("report", "Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.reports.tree.click_path(*self.obj.tree_path)


@navigator.register(ReportsCollection, "ImportExport")
class ImportExportCustomReports(CFMENavigateStep):
    VIEW = ImportExportCustomReportsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self, *args, **kwargs):
        self.prerequisite_view.import_export.tree.click_path("Import / Export", "Custom Reports")
