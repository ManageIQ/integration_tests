# -*- coding: utf-8 -*-

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Region, Select, accordion, fill, flash, form_buttons
from cfme.web_ui.menu import nav

nav.add_branch(
    "reports",
    {
        "import_export": lambda ctx: accordion.tree("Import/Export", "Import / Export"),
    }
)

form = Region(locators=dict(
    export_select=Select("//select[@id='choices_chosen']", multi=True),
    export_button=form_buttons.FormButton("Download Report to YAML"),
    import_overwrite="//input[@id='overwrite']",
    import_file="//input[@id='upload_file']",
    import_submit="//input[@id='upload_atags']"
))

export_select = Select("//select[@id='choices_chosen']", multi=True)
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
