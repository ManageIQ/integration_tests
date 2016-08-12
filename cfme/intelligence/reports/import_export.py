# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from cfme import web_ui as ui
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Region, accordion, fill, flash, form_buttons
from cfme.web_ui.menu import nav

nav.add_branch(
    "reports",
    {
        "import_export": lambda ctx: accordion.tree("Import/Export", "Import / Export"),
    }
)

form = Region(locators=dict(
    export_select=ui.Select("//select[@id='choices_chosen']", multi=True),
    export_button=form_buttons.FormButton("Download Report to YAML"),
    import_overwrite=ui.Input('overwrite'),
    import_file=ui.Input('upload_file'),
    import_submit=ui.Input('upload_atags')
))

export_select = ui.Select("//select[@id='choices_chosen']", multi=True)
export_button = form_buttons.FormButton("Download Report to YAML")


def export_reports(*custom_report_names):
    sel.force_navigate("import_export")
    fill(form.export_select, custom_report_names)
    sel.click(form.export_button)


def import_reports(filename, overwrite=False):
    sel.force_navigate("import_export")
    sel.checkbox(form.import_overwrite, overwrite)
    sel.send_keys(form.import_file, filename)
    sel.click(form.import_submit)
    flash.assert_no_errors()
