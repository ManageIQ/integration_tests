from functools import partial
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Form, Select, accordion, fill, flash, menu, DHTMLSelect
from cfme.web_ui import toolbar as tb
from utils.update import Updateable

cfg_btn = partial(tb.select, "Configuration")
buttons_tree = partial(accordion.tree, "Buttons")

button_group_form = Form(
    fields=[
        ('btn_group_text', "input#name"),
        ('btn_group_hvr_text', "input#description"),
        ('add_button', "//img[@alt='Add']"),
        ('save_button', "//img[@alt='Save Changes']")
    ])

button_form = Form(
    fields=[
        ('btn_text', "input#name"),
        ('btn_hvr_text', "input#description"),
        ('select_dialog', Select("select#dialog_id")),
        ('system_process', Select("select#instance_name")),
        ('request', "input#object_request"),
        ('add_button', "//img[@alt='Add']"),
        ('save_button', "//img[@alt='Save Changes']")
    ])


def _new_button_group(context):
    cfg_btn('Add a new Button Group')
    sel.wait_for_element(button_group_form.btn_group_text)


def _new_button(context):
    cfg_btn('Add a new Button')
    sel.wait_for_element(button_form.btn_text)


menu.nav.add_branch(
    'automate_customization',
    {
        'button_groups':
        [
            lambda _: buttons_tree('Object Types'),
            {
                'button_group_new':
                [
                    lambda _: buttons_tree("Service"),
                    {
                        'new_button_group': _new_button_group
                    }
                ],
                'button_group':
                [
                    lambda ctx: buttons_tree("Service", ctx['buttongroup']),
                    {
                        'group_button_edit': menu.nav.partial(cfg_btn, "Edit this Button Group")
                    }
                ]
            }
        ],
        'buttons':
        [
            lambda _: buttons_tree('Object Types'),
            {
                'button_new':
                [
                    lambda ctx: buttons_tree("Service", ctx['buttongroup']),
                    {
                        'new_button': _new_button
                    }
                ],
                'button':
                [
                    lambda ctx: buttons_tree("Service", ctx['buttongroup'], ctx['button']),
                    {
                        'button_edit': menu.nav.partial(cfg_btn, "Edit this Button")
                    }
                ]
            }
        ]
    }
)


class ButtonGroup(Updateable):
    """Create,Edit and Delete Button Groups

    Args:
        group_text: The button Group name.
        group_hover_text: The button group hover text.
        add: A function to submit the input and create button group.
    """

    def __init__(self, group_text=None, group_hover_text=None):
        self.group_text = group_text
        self.group_hover_text = group_hover_text

    def create(self):
        sel.force_navigate('new_button_group')
        fill(button_group_form, {'btn_group_text': self.group_text,
                                 'btn_group_hvr_text': self.group_hover_text})
        select = DHTMLSelect("div#button_div")
        select.select_by_value(1)
        sel.click(button_group_form.add_button)
        flash.assert_success_message('Buttons Group "%s" was added'
                                     % self.group_hover_text)

    def update(self, updates):
        sel.force_navigate('group_button_edit',
                           context={'buttongroup': self.group_text})
        edited_hvr_text = updates.get('group_hover_text', None)
        fill(button_group_form, {'btn_group_hvr_text': edited_hvr_text})
        sel.click(button_group_form.save_button)
        flash.assert_success_message('Buttons Group "%s" was saved'
                                     % edited_hvr_text)

    def delete(self):
        sel.force_navigate('button_group',
                           context={'buttongroup': self.group_text})
        cfg_btn("Remove this Button Group", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Buttons Group "%s": Delete successful'
                                     % self.group_hover_text)


class Buttons(Updateable):
    """Create,Edit and Delete buttons under a Button

    Args:
        btn_text: The button name.
        btn_hvr_text: The button hover text.
        dialog: The dialog to be selected for a button.
        system: System or Processes , DropDown to choose Automation/Request.
        add: A function to submit the input and create button.
    """

    def __init__(self, buttongroup=None, btn_text=None,
                 btn_hvr_text=None, dialog=None,
                 system=None, request=None):
        self.btngrp = buttongroup
        self.btn_text = btn_text
        self.btn_hvr_text = btn_hvr_text
        self.dialog = dialog
        self.system = system
        self.request = request

    def create(self):
        sel.force_navigate('new_button', context={'buttongroup': self.btngrp})
        fill(button_form, {'btn_text': self.btn_text,
                           'btn_hvr_text': self.btn_hvr_text})
        select = DHTMLSelect("div#button_div")
        select.select_by_value(2)
        fill(button_form, {'select_dialog': self.dialog,
                           'system_process': self.system,
                           'request': self.request})
        sel.click(button_form.add_button)
        flash.assert_success_message('Button "%s" was added'
                                     % self.btn_hvr_text)

    def update(self, updates):
        sel.force_navigate('button_edit', context={'buttongroup': self.btngrp,
                                                   'button': self.btn_text})
        edited_btn_hvr_text = updates.get('btn_hvr_text', None)
        fill(button_form, {'btn_hvr_text': edited_btn_hvr_text})
        sel.click(button_form.save_button)
        flash.assert_success_message('Button "%s" was saved'
                                     % edited_btn_hvr_text)

    def delete(self):
        sel.force_navigate('button', context={'buttongroup': self.btngrp,
                                              'button': self.btn_text})
        cfg_btn("Remove this Button", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Button "%s": Delete successful'
                                     % self.btn_hvr_text)
