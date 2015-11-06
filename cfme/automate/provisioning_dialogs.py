# -*- coding: utf-8 -*-
from functools import partial

from cfme.web_ui.menu import nav

from cfme.exceptions import CandidateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Form, Select, SortTable, accordion, fill, flash, form_buttons, toolbar, \
    Input
from utils import version
from utils.update import Updateable
from utils.pretty import Pretty


acc_tree = partial(accordion.tree, "Provisioning Dialogs")
cfg_btn = partial(toolbar.select, "Configuration")

dialog_table = SortTable({
    version.LOWEST: "//div[@id='records_div']//table[contains(@class, 'style3')]",
    "5.4": "//div[@id='records_div']//table[contains(@class, 'datatable')]",
    "5.5": "//div[@id='records_div']//table[contains(@class, 'table')]"})


def get_dialog_name(o):
    if isinstance(o, basestring):
        return o
    else:
        return o.description

nav.add_branch(
    "automate_customization",
    {
        "host_provision_dialogs":
        lambda _: acc_tree("All Dialogs", "Host Provision"),

        "host_provision_dialog":
        [
            lambda ctx: acc_tree("All Dialogs", "Host Provision", get_dialog_name(ctx["dialog"])),
            {
                "host_provision_dialog_edit": lambda _: cfg_btn("Edit this Dialog")
            }
        ],

        "vm_migrate_dialogs":
        lambda _: acc_tree("All Dialogs", "VM Migrate"),

        "vm_migrate_dialog":
        [
            lambda ctx: acc_tree("All Dialogs", "VM Migrate", get_dialog_name(ctx["dialog"])),
            {
                "vm_migrate_dialog_edit": lambda _: cfg_btn("Edit this Dialog")
            }
        ],

        "vm_provision_dialogs":
        lambda _: acc_tree("All Dialogs", "VM Provision"),

        "vm_provision_dialog":
        [
            lambda ctx: acc_tree("All Dialogs", "VM Provision", get_dialog_name(ctx["dialog"])),
            {
                "vm_provision_dialog_edit": lambda _: cfg_btn("Edit this Dialog")
            }
        ],
    }
)


class DialogTypeSelect(Pretty):
    pretty_attrs = ['loc']

    def __init__(self, loc):
        self._loc = loc

    @property
    def select(self):
        return Select(self._loc)


@fill.method((DialogTypeSelect, tuple))
def _fill_dts_o(dts, tup):
    """To allow our ``constants`` (HOST_PROVISION, ...) being simply assigned, make a wrapper"""
    return fill(dts.select, tup[-1])


class ProvisioningDialog(Updateable, Pretty):
    form = Form(fields=[
        ("name", Input('name')),
        ("description", Input('description')),
        ("type", DialogTypeSelect("//select[@id='dialog_type']")),
        ("content", "//textarea[@id='content_data']"),
    ])

    HOST_PROVISION = ("host_provision", "Host Provision")
    VM_MIGRATE = ("vm_migrate", "VM Migrate")
    VM_PROVISION = ("vm_provision", "VM Provision")
    ALLOWED_TYPES = {HOST_PROVISION, VM_MIGRATE, VM_PROVISION}

    pretty_attrs = ['name', 'description', 'content']

    def __init__(self, type, name=None, description=None, content=None):
        self.name = name
        self.description = description
        self.type = type
        self.content = content

    @property
    def type_nav(self):
        return self.type[0]

    @property
    def exists(self):
        try:
            sel.force_navigate("{}_dialog".format(self.type_nav), context={"dialog": self})
            return True
        except CandidateNotFound:
            return False

    def create(self, cancel=False):
        sel.force_navigate("{}_dialogs".format(self.type_nav))
        cfg_btn("Add a new Dialog")
        fill(self.form, self.__dict__, action=form_buttons.cancel if cancel else form_buttons.add)
        flash.assert_no_errors()

    def update(self, updates):
        sel.force_navigate("{}_dialog".format(self.type_nav), context={"dialog": self})
        cfg_btn("Edit this Dialog")
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        sel.force_navigate("{}_dialog".format(self.type_nav), context={"dialog": self})
        cfg_btn("Remove from the VMDB", invokes_alert=True)
        sel.handle_alert(cancel)

    def change_type(self, new_type):
        """Safely changes type of the dialog. It would normally mess up the navigation"""
        sel.force_navigate("{}_dialog".format(self.type_nav), context={"dialog": self})
        cfg_btn("Edit this Dialog")
        self.type = new_type
        fill(self.form, {"type": new_type}, action=form_buttons.save)
        flash.assert_no_errors()
