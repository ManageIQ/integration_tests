# -*- coding: utf-8 -*-
from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.exceptions import CandidateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Form, Select, SortTable, accordion, fill, flash, form_buttons, toolbar, \
    Input
from utils.appliance import Navigatable
from utils.appliance.endpoints.ui import navigator, navigate_to, CFMENavigateStep
from utils.update import Updateable
from utils.pretty import Pretty
from utils import version


acc_tree = partial(accordion.tree, "Provisioning Dialogs")
cfg_btn = partial(toolbar.select, "Configuration")

dialog_table = SortTable("//div[@id='records_div']//table[contains(@class, 'table')]")


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


class ProvisioningDialog(Updateable, Pretty, Navigatable):
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

    def __init__(self, type, name=None, description=None, content=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.description = description
        self.type = type
        self.content = content

    def __str__(self):
        return self.name

    @property
    def type_nav(self):
        return self.type[0]

    @property
    def type_tree_nav(self):
        return self.type[1]

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False

    def create(self, cancel=False):
        navigate_to(self, 'Add')
        fill(self.form, self.__dict__, action=form_buttons.cancel if cancel else form_buttons.add)
        flash.assert_no_errors()

    def update(self, updates):
        navigate_to(self, 'Edit')
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        navigate_to(self, 'Details')
        if version.current_version() >= '5.7':
            btn_name = "Remove Dialog"
        else:
            btn_name = "Remove from the VMDB"
        cfg_btn(btn_name, invokes_alert=True)
        sel.handle_alert(cancel)

    def change_type(self, new_type):
        """Safely changes type of the dialog. It would normally mess up the navigation"""
        navigate_to(self, 'Edit')
        self.type = new_type
        fill(self.form, {"type": new_type}, action=form_buttons.save)
        flash.assert_no_errors()


@navigator.register(ProvisioningDialog, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Automate', 'Customization')(None)

    def resetter(self):
        accordion.tree("Provisioning Dialogs", "All Dialogs")


@navigator.register(ProvisioningDialog, 'Add')
class New(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Provisioning Dialogs", "All Dialogs", self.obj.type_tree_nav)
        cfg_btn("Add a new Dialog")


@navigator.register(ProvisioningDialog, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Provisioning Dialogs", "All Dialogs", self.obj.type_tree_nav,
            self.obj.description)


@navigator.register(ProvisioningDialog, 'Edit')
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn("Edit this Dialog")
