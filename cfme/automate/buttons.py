# -*- coding: utf-8 -*-
from functools import partial
from cfme import web_ui as ui
from cfme.exceptions import CandidateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Form, accordion, fill, flash, form_buttons, menu, DHTMLSelect, AngularSelect
from cfme.web_ui import toolbar as tb
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


def _new_button_group(_context):
    cfg_btn('Add a new Button Group')
    sel.wait_for_element(button_group_form.btn_group_text)


def _new_button(_context):
    cfg_btn('Add a new Button')
    sel.wait_for_element(button_form.btn_text)


menu.nav.add_branch(
    'automate_customization',
    {
        'button_group_category':
        [
            lambda ctx: buttons_tree(ctx['buttongroup'].type),
            {
                'new_button_group': _new_button_group
            }
        ],
        'button_group':
        [
            lambda ctx: buttons_tree(ctx['buttongroup'].type, ctx['buttongroup'].text),
            {
                'group_button_edit': menu.nav.partial(cfg_btn, "Edit this Button Group")
            }
        ],
        'button_new':
        [
            lambda ctx: buttons_tree(ctx['buttongroup'].type, ctx['buttongroup'].text),
            {
                'new_button': _new_button
            }
        ],
        'button':
        [
            lambda ctx: buttons_tree(
                ctx['button'].group.type, ctx['button'].group.text, ctx['button'].text),
            {
                'button_edit': menu.nav.partial(cfg_btn, "Edit this Button")
            }
        ],
    }
)


class ButtonGroup(Updateable):
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

    def __init__(self, text=None, hover=None, type=None):
        self.text = text
        self.hover = hover
        self.type = type

    def create(self):
        sel.force_navigate('new_button_group', context={"buttongroup": self})
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
        sel.force_navigate('group_button_edit', context={"buttongroup": self})
        edited_hvr_text = updates.get('hover', None)
        fill(button_group_form, {'btn_group_hvr_text': edited_hvr_text})
        sel.click(button_group_form.save_button)
        flash.assert_success_message('Buttons Group "{}" was saved'.format(edited_hvr_text))

    def delete(self):
        sel.force_navigate('button_group', context={"buttongroup": self})
        cfg_btn("Remove this Button Group", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Buttons Group "{}": Delete successful'.format(self.hover))

    @property
    def exists(self):
        try:
            sel.force_navigate('button_group', context={"buttongroup": self})
            return True
        except CandidateNotFound:
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()


class Button(Updateable):
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
                 system=None, request=None):
        self.group = group
        self.text = text
        self.hover = hover
        self.dialog = dialog
        self.system = system
        self.request = request

    def create(self):
        sel.force_navigate('new_button', context={'buttongroup': self.group})
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
        sel.force_navigate('button_edit', context={'button': self})
        edited_hover = updates.get('hover', None)
        fill(button_form, {'btn_hvr_text': edited_hover})
        sel.click(button_form.save_button)
        flash.assert_success_message('Button "{}" was saved'.format(edited_hover))

    def delete(self):
        sel.force_navigate('button', context={'button': self})
        cfg_btn("Remove this Button", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Button "{}": Delete successful'.format(self.hover))

    @property
    def exists(self):
        try:
            sel.force_navigate('button', context={"button": self})
            return True
        except CandidateNotFound:
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()
