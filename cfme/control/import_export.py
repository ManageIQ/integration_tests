# -*- coding: utf-8 -*-
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Form, Region, fill, flash


import_form = Form(
    fields=[
        ("file_select", "//input[@id='upload_file']"),
        ("upload_button", "//input[@id='upload_atags']")
    ]
)


def make_button(button_alt):
    return "//div[@id='buttons']/ul[@id='form_buttons']/li/a/img[@alt='%s']" % button_alt


upload_buttons = Region(
    locators=dict(
        commit_button=make_button("Commit Import"),
        cancel_button=make_button("Cancel Import"),
    )
)


def import_file(filename, cancel=False):
    """ Go to Control / Import Export and import given file.

    Args:
        filename: Full path to file to import.
        cancel: Whether to click Cancel instead of commit.
    """
    sel.force_navigate("control_import_export")
    fill(
        import_form,
        {"file_select": filename},
    )
    sel.click(import_form.upload_button)
    flash.assert_no_errors()
    return sel.click(upload_buttons.cancel_button if cancel else upload_buttons.commit_button)
