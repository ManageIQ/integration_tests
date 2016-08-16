# -*- coding: utf-8 -*-
"""Module handling definition, CRUD, queuing Reports.

Extensively uses :py:mod:`cfme.intelligence.reports.ui_elements`
"""
from functools import partial

from cached_property import cached_property

from cfme.fixtures import pytest_selenium as sel
from cfme.intelligence.reports.ui_elements import (ColumnHeaderFormatTable, ColumnStyleTable,
    RecordGrouper)
from cfme.web_ui import (CAndUGroupTable, Form, Table, Select, ShowingInputs, accordion, fill,
    flash, form_buttons, paginator, table_in_object, tabstrip, toolbar)
from cfme.web_ui.expression_editor import Expression
from cfme.web_ui.menu import nav
from cfme.web_ui.tabstrip import TabStripForm
from cfme.web_ui.multibox import MultiBoxSelect
from utils import db
from utils.update import Updateable
from utils.wait import wait_for
from utils.pretty import Pretty


def get_report_name(o):
    if isinstance(o, CustomReport):
        return o.menu_name
    else:
        return str(o)


def reload_view():
    """Reloads and keeps on the current tabstrip page"""
    current = tabstrip.get_selected_tab()
    toolbar.select("Reload current display")
    tabstrip.select_tab(current)


cfg_btn = partial(toolbar.select, "Configuration")
download_btn = partial(toolbar.select, "Download")

nav.add_branch(
    "reports",
    {
        "reports_all":
        [
            lambda ctx: accordion.tree("Reports", "All Reports"),
            {
                "report_add":
                lambda ctx: cfg_btn("Add a new Report"),
            }
        ],

        "report_canned":
        [
            lambda ctx: accordion.tree("Reports", "All Reports", *ctx["path"]),
            {
                "report_canned_info":
                [
                    lambda ctx: tabstrip.select_tab("Report Info"),
                    {
                        # Empty for now
                    },
                ],

                "report_canned_saved": lambda ctx: tabstrip.select_tab("Saved Reports"),
            }
        ],

        "reports_custom":
        lambda ctx: accordion.tree(
            "Reports", "All Reports", "{} (All EVM Groups)".format(
                db.get_yaml_config("vmdb")["server"]["company"]
            ), "Custom",
        ),

        "report_custom":
        [
            lambda ctx: accordion.tree(
                "Reports", "All Reports", "{} (All EVM Groups)".format(
                    db.get_yaml_config("vmdb")["server"]["company"]
                ), "Custom",
                get_report_name(ctx["report"])
            ),
            {
                "report_custom_info":
                [
                    lambda ctx: tabstrip.select_tab("Report Info"),
                    {
                        "report_custom_edit": lambda ctx: cfg_btn("Edit this Report"),
                    },
                ],

                "report_custom_saved": lambda ctx: tabstrip.select_tab("Saved Reports"),
            }
        ],

        "saved_report_custom":
        lambda ctx: accordion.tree(
            "Reports", "All Reports", "{} (All EVM Groups)".format(
                db.get_yaml_config("vmdb")["server"]["company"]),
            "Custom", get_report_name(ctx["report"]), ctx["datetime"]
        ),

        "saved_report_canned":
        lambda ctx: accordion.tree(
            "Reports", *(["All Reports"] + ctx["path"] + [ctx["datetime"]])
        ),
    }
)


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
img = partial(tag, "img")
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
                img(alt="Move selected fields up"),
                img(alt="Move selected fields down"),
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


class CustomReport(Updateable):
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

    def __init__(self, **values):
        # We will override the original dict
        self.__dict__ = dict(self._default_dict)
        self.__dict__.update(values)
        # We need to pass the knowledge whether it is a candu report
        try:
            self.is_candu
        except AttributeError:
            self.is_candu = False

    def create(self, cancel=False):
        sel.force_navigate("report_add")
        fill(report_form, self, action=form_buttons.cancel if cancel else form_buttons.add)
        flash.assert_no_errors()

    def update(self, updates):
        sel.force_navigate("report_custom_edit", context={"report": self})
        fill(report_form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        sel.force_navigate("report_custom_info", context={"report": self})
        toolbar.select("Configuration", "Delete this Report from the Database", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()

    def get_saved_reports(self):
        sel.force_navigate("report_custom_saved", context={"report": self})
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
        sel.force_navigate("report_custom_info", context={"report": self})
        toolbar.select("Queue")
        flash.assert_no_errors()
        if wait_for_finish:
            # Get the queued_at value to always target the correct row
            queued_at = sel.text(list(records_table.rows())[0].queued_at)

            def _get_state():
                row = records_table.find_row("queued_at", queued_at)
                status = sel.text(row.status).strip().lower()
                assert status != "error", sel.text(row)
                return status == "finished"

            wait_for(
                _get_state,
                delay=1,
                message="wait for report generation finished",
                fail_func=reload_view,
                num_sec=300,
            )


class CustomSavedReport(Updateable, Pretty):
    """Custom Saved Report. Enables us to retrieve data from the table.

    Args:
        report: Report that we have data from.
        datetime: Datetime of "Run At" of the report. That's what :py:func:`queue_canned_report`
            returns.
        candu: If it is a C&U report, in that case it uses a different table.
    """
    _table_loc = "//div[@id='report_html_div']/table[thead]"

    pretty_attrs = ['report', 'datetime']

    def __init__(self, report, datetime, candu=False):
        self.report = report
        self.datetime = datetime
        self.candu = candu

    def navigate(self):
        if not self._on_report_page:
            return sel.force_navigate(
                "saved_report_custom", context={"report": self.report, "datetime": self.datetime}
            )
        else:
            return True

    @property
    def _table(self):
        """This is required to prevent the StaleElementReference for different instances"""
        if self.candu:
            return CAndUGroupTable(self._table_loc)
        else:
            return Table(self._table_loc)

    @property
    def _on_report_page(self):
        return sel.is_displayed(
            "//div[@class='dhtmlxInfoBarLabel' and contains(., 'Saved Report \"{} {}')]".format(
                self.report.title, self.datetime
            )
        )

    @cached_property
    def data(self):
        """Retrieves data from the saved report.

        Returns: :py:class:`SavedReportData` if it is not a candu report. If it is, then it returns
            a list of groups in the table.
        """
        self.navigate()
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
        self.navigate()
        extensions_mapping = {'txt': 'Text', 'csv': 'CSV', 'pdf': 'PDF'}
        try:
            download_btn("Download as {}".format(extensions_mapping[extension]))
        except:
            raise ValueError("Unknown extention. check the extentions_mapping")


class CannedSavedReport(CustomSavedReport):
    """As we cannot create or edit canned reports, we don't know their titles and so, so we
    need to change the navigation a little bit for it to work correctly.

    Args:
        path_to_report: Iterable with path to report.
        datetime: Datetime of "Run At" of the report. That's what :py:func:`queue_canned_report`
            returns.
    """
    def __init__(self, path_to_report, datetime, candu=False):
        self.path = path_to_report
        self.datetime = datetime
        self.candu = candu

    def navigate(self):
        return sel.force_navigate(
            "saved_report_canned", context={"path": self.path, "datetime": self.datetime}
        )

    @classmethod
    def new(cls, path):
        return cls(path, queue_canned_report(*path))


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


def queue_canned_report(*path):
    """Queue report from selection of pre-prepared reports.

    Args:
        *path: Path in tree after All Reports
    Returns: Value of Run At in the table so the run can be then checked.
    """
    sel.force_navigate("report_canned_info", context={"path": path})
    toolbar.select("Queue")
    flash.assert_no_errors()
    tabstrip.select_tab("Saved Reports")
    queued_at = sel.text(list(records_table.rows())[0].queued_at)

    def _get_state():
        row = records_table.find_row("queued_at", queued_at)
        status = sel.text(row.status).strip().lower()
        assert status != "error", sel.text(row)
        return status == "finished"

    wait_for(
        _get_state,
        delay=1,
        message="wait for report generation finished",
        fail_func=reload_view
    )
    return sel.text(list(records_table.rows())[0].run_at).encode("utf-8")


def get_saved_canned_reports(*path):
    sel.force_navigate("report_canned_saved", context={"path": path})
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
