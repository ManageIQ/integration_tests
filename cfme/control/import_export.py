# -*- coding: utf-8 -*-
from selenium.common.exceptions import NoSuchElementException

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Form, Region, Select, fill, flash
from cfme.web_ui.form_buttons import FormButton


import_form = Form(
    fields=[
        ("file_select", "#upload_file"),
        ("upload_button", "//input[@id='upload_atags' or @id='upload_tags']")
    ]
)

export_form = Form(
    fields=[
        ("type", Select("select#dbtype")),
        ("available", Select("select#choices_chosen_")),
    ]
)

upload_buttons = Region(
    locators=dict(
        commit_button=FormButton("Commit Import"),
        cancel_button=FormButton("Cancel Import"),
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


def is_imported(policy_profile):
    sel.force_navigate("control_import_export")
    try:
        export_form.available.select_by_visible_text(str(policy_profile))
        return True
    except NoSuchElementException:
        return False
