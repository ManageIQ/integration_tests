# -*- coding: utf-8 -*-
from cfme.web_ui import menu
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Form, fill, accordion
from datetime import datetime


def open_import_export(_):
    accordion.tree("Import/Export", "Service Dialog Import/Export")


export_form = Form(
    fields=[
        ('dialog_multiselect', "//select[@id='service_dialogs_']"),
        ('_export_button', "//input[@type='image']"),
    ]
)

menu.nav.add_branch(
    'automate_customization',
    {
        "import_export": open_import_export,
    })


class SeedingDialog():
    _export_button = "input([@type='image'])"

    def __init__(self, dialog=None):
        self.dialog = dialog

    def export_dialog(self):
        """ Go to Automate / Customization/ Import Export and export created dialog.

        Args:
            dialog: Dialog to export.
        """
        sel.force_navigate("import_export")
        fill(export_form, {'dialog_multiselect': self.dialog})
        sel.click(export_form._export_button)
        x = datetime.utcnow()
        timestamp = x.strftime("%Y%m%d_%H%M%S")
        return timestamp
