# -*- coding: utf-8 -*-
"""Module handling definition, CRUD, queuing Reports.

Extensively uses :py:mod:`cfme.intelligence.reports.ui_elements`
"""
from functools import partial

from cached_property import cached_property
from navmazing import NavigateToSibling, NavigateToAttribute, NavigateToObject
from cfme.fixtures import pytest_selenium as sel
from cfme.intelligence.reports.ui_elements import (ColumnHeaderFormatTable, ColumnStyleTable,
    RecordGrouper)
from cfme.web_ui import (CAndUGroupTable, Form, Table, Select, ShowingInputs, accordion, fill,
    flash, form_buttons, paginator, table_in_object, tabstrip, toolbar, CheckboxTable)
from cfme.web_ui.expression_editor import Expression
from cfme.web_ui.tabstrip import TabStripForm
from cfme.web_ui.multibox import MultiBoxSelect
from utils.update import Updateable
from utils.wait import wait_for
from utils.pretty import Pretty
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from utils import version
from utils.timeutil import parsetime


def reload_view():
    """Reloads and keeps on the current tabstrip page"""
    current = tabstrip.get_selected_tab()
    toolbar.select("Reload current display")
    tabstrip.select_tab(current)


cfg_btn = partial(toolbar.select, "Configuration")
download_btn = partial(toolbar.select, "Download")


# I like this but it will have to go away later
def tag(tag_name, **kwargs):
    prefix = "//{}".format(tag_name)
    if kwargs:
        return prefix + "[{}]".format(
            " and ".join(["@{}='{}'".format(k, v) for k, v in kwargs.iteritems()])
        )
    else:
        return prefix

input = partial(tag, "input")
select = lambda **kwargs: Select(tag("select", **kwargs))
button = partial(tag, "button")
table = partial(tag, "table")

report_form = TabStripForm(
    # These are displayed always
    fields=[
        ("menu_name", input(id="name")),
        ("title", input(id="title")),
    ],
    tab_fields={
        "Columns": [
            ("base_report_on", select(id="chosen_model")),
            ("report_fields", MultiBoxSelect(
                select(id="available_fields"),
                select(id="selected_fields"),
                button(alt="Move selected fields up"),
                button(alt="Move selected fields down"),
            )),
            ("cancel_after", select(id="chosen_queue_timeout")),
        ],
        "Consolidation": [
            ("group_records", ShowingInputs(
                select(id="chosen_pivot1"),
                select(id="chosen_pivot2"),
                select(id="chosen_pivot3"),
            )),
            ("calculations_grouped", RecordGrouper(
                table_in_object("Specify Calculations of Numeric Values for Grouped Records"))),
        ],
        "Formatting": [
            ("page_size", select(id="pdf_page_size")),
            ("headers",
                ColumnHeaderFormatTable(table_in_object("Specify Column Headers and Formats"))),
        ],
        "Styling": [
            ("column_styles", ColumnStyleTable("styling_div")),
        ],
        "Filter": [
            ("filter", Expression()),
            ("filter_show_costs", select(id="cb_show_typ")),
            ("filter_owner", select(id="cb_owner_id")),
            ("filter_tag_cat", select(id="cb_tag_cat")),
            ("filter_tag_value", select(id="cb_tag_value")),
            ("interval_end", select(id="cb_end_interval_offset")),
        ],
        "Summary": [
            ("sort", ShowingInputs(
                Form(fields=[
                    ("by", select(id="chosen_sort1")),
                    ("order", select(id="sort_order")),
                    ("breaks", select(id="sort_group")),
                ]),
                Form(fields=[
                    ("by", select(id="chosen_sort2")),
                    ("limit", select(id="row_limit")),
                ]),
            )),
        ],
        "Charts": [
            ("chart_type", select(id="chosen_graph")),
            ("top_values", select(id="chosen_count")),
            ("sum_other", input(id="chosen_other")),
        ],
        "Timeline": [
            ("base_timeline_on", select(id="chosen_tl")),
            ("band_units", ShowingInputs(
                select(id="chosen_unit1"),
                select(id="chosen_unit2"),
                select(id="chosen_unit3"),
                min_values=1
            )),
            ("event_position", select(id="chosen_position")),
            ("show_event_unit", select(id="chosen_last_unit")),
            ("show_event_count", select(id="chosen_last_time")),
        ],
        "Preview": [],
    },
    # This will go away after the order of the tabs will be guaranteed
    order=["Columns", "Consolidation", "Formatting", "Styling", "Filter", "Summary", "Charts"]
)

records_table = Table("//div[@id='records_div']//table[thead]")


class CustomReport(Updateable, Navigatable):
    _default_dict = {
        "menu_name": None,
        "title": None,
        "base_report_on": None,
        "report_fields": None,
        "cancel_after": None,
        "group_records": None,
        "calculations_grouped": None,
        "page_size": None,
        "headers": None,
        "column_styles": None,
        "filter": None,
        "filter_show_costs": None,
        "filter_owner": None,
        "filter_tag_cat": None,
        "filter_tag_value": None,
        "sort": None,
        "chart_type": None,
        "top_values": None,
        "sum_other": None,
        "base_timeline_on": None,
        "band_units": None,
        "event_position": None,
        "show_event_unit": None,
        "show_event_count": None
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
        navigate_to(self, 'New')
        fill(report_form, self, action=form_buttons.cancel if cancel else form_buttons.add)
        flash.assert_no_errors()

    def update(self, updates):
        navigate_to(self, 'Edit')
        fill(report_form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        navigate_to(self, 'Details')
        toolbar.select("Configuration", "Delete this Report from the Database", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()

    def get_saved_reports(self):
        navigate_to(self, 'Saved')
        results = []
        try:
            for page in paginator.pages():
                sel.wait_for_element(records_table)
                for row in records_table.rows():
                    results.append(
                        CustomSavedReport(self, sel.text(row.run_at).encode("utf-8"), self.is_candu)
                    )
        except sel.NoSuchElementException:
            pass
        return results

    def queue(self, wait_for_finish=False):
        navigate_to(self, 'Details')
        toolbar.select("Queue")
        flash.assert_no_errors()
        if wait_for_finish:
            # Get the queued_at value to always target the correct row
            queued_at = sel.text(list(records_table.rows())[0].queued_at)

            def _get_state():
                row = records_table.find_row("queued_at", queued_at)
                status = sel.text(row.status).strip().lower()
                assert status != "error", sel.text(row)
                return status == version.pick({"5.6": "finished",
                                               "5.7": "complete"})

            wait_for(
                _get_state,
                delay=1,
                message="wait for report generation finished",
                fail_func=reload_view,
                num_sec=300,
            )


@navigator.register(CustomReport, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Cloud Intel', 'Reports')(None)
        accordion.tree("Reports", "All Reports")


@navigator.register(CustomReport, 'New')
class New(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn("Add a new Report")


@navigator.register(CustomReport, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree(
            "Reports", "All Reports", "{} (All EVM Groups)".format(
                self.obj.appliance.company_name), "Custom",
            self.obj.menu_name)
        tabstrip.select_tab("Report Info")


@navigator.register(CustomReport, 'Edit')
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn("Edit this Report")


@navigator.register(CustomReport, 'Saved')
class Saved(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        tabstrip.select_tab("Saved Reports")


class CustomSavedReport(Updateable, Pretty, Navigatable):
    """Custom Saved Report. Enables us to retrieve data from the table.

    Args:
        report: Report that we have data from.
        datetime: Datetime of "Run At" of the report. That's what :py:func:`queue_canned_report`
            returns.
        candu: If it is a C&U report, in that case it uses a different table.
    """
    _table_loc = "//div[@id='report_html_div']/table[thead]"

    pretty_attrs = ['report', 'datetime']

    def __init__(self, report, datetime, candu=False, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.report = report
        self.datetime = datetime
        self.candu = candu
        self.datetime_in_tree = version.pick({"5.6": self.datetime,
                        "5.7": parsetime.from_american_with_utc(self.datetime).to_iso_with_utc()})

    @property
    def _table(self):
        """This is required to prevent the StaleElementReference for different instances"""
        if self.candu:
            return CAndUGroupTable(self._table_loc)
        else:
            return Table(self._table_loc)

    @cached_property
    def data(self):
        """Retrieves data from the saved report.

        Returns: :py:class:`SavedReportData` if it is not a candu report. If it is, then it returns
            a list of groups in the table.
        """
        navigate_to(self, "Details")
        if isinstance(self._table, CAndUGroupTable):
            return list(self._table.groups())
        try:
            headers = tuple([sel.text(hdr).encode("utf-8") for hdr in self._table.headers])
            body = []
            for page in paginator.pages():
                for row in self._table.rows():
                    row_data = tuple([sel.text(row[header]).encode("utf-8") for header in headers])
                    body.append(row_data)
        except sel.NoSuchElementException:
            # No data found
            return SavedReportData([], [])
        else:
            return SavedReportData(headers, body)

    def download(self, extension):
        navigate_to(self, "Details")
        extensions_mapping = {'txt': 'Text', 'csv': 'CSV', 'pdf': 'PDF'}
        try:
            download_btn("Download as {}".format(extensions_mapping[extension]))
        except:
            raise ValueError("Unknown extention. check the extentions_mapping")


@navigator.register(CustomSavedReport, 'Details')
class SavedDetails(CFMENavigateStep):
    prerequisite = NavigateToObject(CustomReport, 'All')

    def step(self):
        accordion.tree(
            "Reports", "All Reports", "{} (All EVM Groups)".format(
                self.obj.appliance.company_name),
            "Custom", self.obj.report.menu_name, self.obj.datetime_in_tree)

    def am_i_here(self):
        return sel.is_displayed(
            "//div[@class='dhtmlxInfoBarLabel' and contains(., 'Saved Report \"{} {}')]".format(
                self.obj.report.title, self.obj.datetime_in_tree
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
    saved_table = CheckboxTable('//div[@id="records_div"]//table')

    def __init__(self, path_to_report, datetime, candu=False, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.path = path_to_report
        self.datetime = datetime
        self.candu = candu
        self.datetime_in_tree = version.pick({"5.6": self.datetime,
                        "5.7": parsetime.from_american_with_utc(self.datetime).to_iso_with_utc()})

    def navigate(self):
        navigate_to(self, "Details")

    @classmethod
    def new(cls, path):
        return cls(path, cls.queue_canned_report(path))

    @classmethod
    def queue_canned_report(cls, path):
        """Queue report from selection of pre-prepared reports.

        Args:
            *path: Path in tree after All Reports
        Returns: Value of Run At in the table so the run can be then checked.
        """
        cls.path = path
        navigate_to(cls, "Info")
        toolbar.select("Queue")
        flash.assert_no_errors()
        tabstrip.select_tab("Saved Reports")
        queued_at = sel.text(list(records_table.rows())[0].queued_at)

        def _get_state():
            row = records_table.find_row("queued_at", queued_at)
            status = sel.text(row.status).strip().lower()
            assert status != "error", sel.text(row)
            return status == version.pick({"5.6": "finished",
                                           "5.7": "complete"})

        wait_for(
            _get_state,
            delay=1,
            message="wait for report generation finished",
            fail_func=reload_view
        )
        return sel.text(list(records_table.rows())[0].run_at).encode("utf-8")

    def get_saved_canned_reports(self, *path):
        navigate_to(self, "Saved")
        results = []
        try:
            for page in paginator.pages():
                for row in records_table.rows():
                    results.append(
                        CannedSavedReport(path, sel.text(row.run_at).encode("utf-8"))
                    )
        except sel.NoSuchElementException:
            pass
        return results

    def delete(self):
        navigate_to(self, 'Saved')
        self.saved_table.select_row(header='Run At', value=self.datetime_in_tree)
        cfg_btn("Delete this Saved Report from the Database", invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()


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
