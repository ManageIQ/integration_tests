# -*- coding: utf-8 -*-
from functools import partial

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import accordion, toolbar
from cfme.web_ui.menu import nav
from cfme.web_ui.tables import Table


nav.add_branch(
    "reports",
    {
        "saved_reports":
        lambda ctx: accordion.tree("Saved Reports", "All Saved Reports"),

        "saved_reports_for":
        [
            lambda ctx: accordion.tree("Saved Reports", "All Saved Reports", ctx["report_name"]),
            {
                "saved_report":
                lambda ctx: reports_table.click_cell("queued_at", ctx["date_time_completed"]),
            }
        ],
    }
)

reports_table = Table.create("//div[@id='records_div']//table[thead]", {'checkbox'})
cfg_btn = partial(toolbar.select, "Configuration")


def get_saved_reports_for(name):
    sel.force_navigate("saved_reports_for", context={"report_name": name})
    dates = []
    try:
        for row in reports_table.rows():
            dates.append(sel.text(row.queued_at).encode("utf-8").strip())
    except sel.NoSuchElementException:
        pass
    return dates


def go_to_latest_saved_report_for(name):
    latest = get_saved_reports_for(name)[0]
    sel.force_navigate(
        "saved_report",
        context={"report_name": name, "date_time_completed": latest},
        start="saved_reports_for"
    )


def show_full_screen(cancel=False):
    cfg_btn("Show full screen report", invokes_alert=True)
    sel.handle_alert(cancel)


def delete_saved_report(cancel=False):
    cfg_btn("Delete this Saved Report from the Database", invokes_alert=True)
    sel.handle_alert(cancel)
