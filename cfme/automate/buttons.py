# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling, NavigateToAttribute

from functools import partial
from cfme import web_ui as ui
from cfme.exceptions import CandidateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Form, accordion, fill, flash, form_buttons, DHTMLSelect, AngularSelect
from cfme.web_ui import toolbar as tb
from utils.appliance import Navigatable
from utils.appliance.endpoints.ui import navigator, navigate_to, CFMENavigateStep
from utils.update import Updateable
from utils import deferred_verpick, version

cfg_btn = partial(tb.select, "Configuration")
buttons_tree = partial(accordion.tree, "Buttons", "Object Types")

button_group_form = Form(
    fields=[
        ('btn_group_text', ui.Input('name')),
        ('btn_group_hvr_text', ui.Input('description')),
        ('add_button', form_buttons.add),
        ('save_button', form_buttons.save)
    ])

button_form = Form(
    fields=[
        ('btn_text', ui.Input('name')),
        ('btn_hvr_text', ui.Input('description')),
        ('select_dialog', ui.Select('select#dialog_id')),
        ('system_process', ui.Select('select#instance_name')),
        ('request', ui.Input('object_request')),
        ('add_button', form_buttons.add),
        ('save_button', form_buttons.save)
    ])


class ButtonGroup(Updateable, Navigatable):
    """Create,Edit and Delete Button Groups

    Args:
        text: The button Group name.
        hover: The button group hover text.
        type: The object type.
    """
    CLUSTER = "Cluster"
    DATASTORE = "Datastore"
    HOST = deferred_verpick({
        version.LOWEST: "Host",
        '5.4': "Host / Node"}
    )
    PROVIDER = "Provider"
    SERVICE = "Service"
    TEMPLATE = "VM Template and Image"
    VM_INSTANCE = "VM and Instance"

    def __init__(self, text=None, hover=None, type=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.text = text
        self.hover = hover
        self.type = type

    def create(self):
        navigate_to(self, 'Add')

        fill(button_group_form, {'btn_group_text': self.text,
                                 'btn_group_hvr_text': self.hover})
        if version.current_version() < "5.5":
            select = DHTMLSelect("div#button_div")
        else:
            select = AngularSelect("button_image")
        select.select_by_value(1)
        sel.click(button_group_form.add_button)
        flash.assert_success_message('Buttons Group "{}" was added'.format(self.hover))

    def update(self, updates):
        navigate_to(self, 'Edit')
        edited_hvr_text = updates.get('hover', None)
        fill(button_group_form, {'btn_group_hvr_text': edited_hvr_text})
        sel.click(button_group_form.save_button)
        flash.assert_success_message('Buttons Group "{}" was saved'.format(edited_hvr_text))

    def delete(self):
        navigate_to(self, 'Details')
        cfg_btn("Remove this Button Group", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Buttons Group "{}": Delete successful'.format(self.hover))

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()


@navigator.register(ButtonGroup, 'All')
class ButtonGroupAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Automate', 'Customization')(None)

    def resetter(self):
        accordion.tree("Buttons", "Object Types")


@navigator.register(ButtonGroup, 'Add')
class ButtonGroupNew(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Buttons", "Object Types", self.obj.type)
        cfg_btn('Add a new Button Group')
        sel.wait_for_element(button_group_form.btn_group_text)


@navigator.register(ButtonGroup, 'Details')
class ButtonGroupDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Buttons", "Object Types", self.obj.type, self.obj.text)


@navigator.register(ButtonGroup, 'Edit')
class ButtonGroupEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn("Edit this Button Group")


class Button(Updateable, Navigatable):
    """Create,Edit and Delete buttons under a Button

    Args:
        group: Group where this button belongs.
        text: The button name.
        hover: The button hover text.
        dialog: The dialog to be selected for a button.
        system: System or Processes , DropDown to choose Automation/Request.
    """

    def __init__(self, group=None, text=None,
                 hover=None, dialog=None,
                 system=None, request=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.group = group
        self.text = text
        self.hover = hover
        self.dialog = dialog
        self.system = system
        self.request = request

    def create(self):
        navigate_to(self, 'Add')
        fill(button_form, {'btn_text': self.text,
                           'btn_hvr_text': self.hover})
        if version.current_version() < "5.5":
            select = DHTMLSelect("div#button_div")
        else:
            select = AngularSelect("button_image")
        select.select_by_value(2)
        fill(button_form, {'select_dialog': self.dialog.label if self.dialog is not None else None,
                           'system_process': self.system,
                           'request': self.request})
        sel.click(button_form.add_button)
        flash.assert_success_message('Button "{}" was added'.format(self.hover))

    def update(self, updates):
        navigate_to(self, 'Edit')
        edited_hover = updates.get('hover', None)
        fill(button_form, {'btn_hvr_text': edited_hover})
        sel.click(button_form.save_button)
        flash.assert_success_message('Button "{}" was saved'.format(edited_hover))

    def delete(self):
        navigate_to(self, 'Details')
        cfg_btn("Remove this Button", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Button "{}": Delete successful'.format(self.hover))

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()


@navigator.register(Button, 'All')
class ButtonAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Automate', 'Customization')(None)

    def resetter(self):
        accordion.tree("Buttons", "Object Types")


@navigator.register(Button, 'Add')
class ButtonNew(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Buttons", "Object Types", self.obj.group.type, self.obj.group.text)
        cfg_btn('Add a new Button')
        sel.wait_for_element(button_form.btn_text)


@navigator.register(Button, 'Details')
class ButtonDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree(
            "Buttons", "Object Types", self.obj.group.type, self.obj.group.text, self.obj.text)


@navigator.register(Button, 'Edit')
class ButtonEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn("Edit this Button")
