#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import ui_navigate as nav
import cfme
import cfme.web_ui.menu  # so that menu is already loaded before grafting onto it
from cfme.web_ui import Region, Form
import cfme.web_ui.flash as flash
import cfme.fixtures.pytest_selenium as browser
import utils.conf as conf
from cfme.web_ui import fill


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
    nav.go_to("control_import_export")
    fill(
        import_form,
        {"file_select": filename},
        action=import_form.upload_button
    )
    flash.assert_no_errors()
    return browser.click(upload_buttons.cancel_button if cancel else upload_buttons.commit_button)
