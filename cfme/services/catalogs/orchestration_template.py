# -*- coding: utf-8 -*-
from functools import partial
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import accordion, fill, form_buttons, menu, Form, Input, flash, Select, ScriptBox
from cfme.web_ui import toolbar as tb
from utils.update import Updateable
from utils.pretty import Pretty

cfg_btn = partial(tb.select, "Configuration")
accordion_tree = partial(accordion.tree, "Orchestration Templates")

dialog_form = Form(
    fields=[
        ('dialog_name', Input("dialog_name")),
        ('save_button', form_buttons.save)
    ])

create_template_form = Form(
    fields=[
        ('template_name', Input("name")),
        ('description', "textarea#description"),
        ("template_type", Select("select#type")),
        ('content', ScriptBox(name="miqEditor",
                    ta_locator="//div[@id='basic_info_div']/div/div"
                    "/div/div/div/div/div/div/pre/span")),
        ('add_button', form_buttons.add),
        ('edit_button', form_buttons.save),
    ])


def _orch_templates_create_dialog(context):
    accordion_tree('All Orchestration Templates',
        context['template_type'], context['template_name'])
    cfg_btn('Create Service Dialog from Orchestration Template')


menu.nav.add_branch(
    'services_catalogs',
    {
        'orchestration_templates':
        [
            lambda _: accordion.click('Orchestration Templates'),
            {
                'select_template':
                [
                    lambda ctx: accordion_tree('All Orchestration Templates',
                        ctx['template_type'], ctx['template_name']),
                    {'edit_template': lambda _: cfg_btn("Edit this Orchestration Template"),
                     'create_service_dialog': lambda _: cfg_btn("Create Service Dialog from "
                        "Orchestration Template")}
                ],
                'orch_template_type':
                [
                    lambda ctx: accordion_tree(
                        'All Orchestration Templates', ctx['template_type']),
                    {'create_new_template': lambda _: cfg_btn("Create new Orchestration Template")}
                ]
            }
        ]
    }
)


class OrchestrationTemplate(Updateable, Pretty):
    pretty_attrs = ['template_type', 'template_name']

    def __init__(self, template_type=None, template_name=None, description=None):
        self.template_type = template_type
        self.template_name = template_name
        self.description = description

    def create(self, content):
        sel.force_navigate('create_new_template',
                           context={'template_type': self.template_type})
        if(self.template_type == "CloudFormation Templates"):
            temp_type = "Amazon CloudFormation"
        else:
            temp_type = "OpenStack Heat"
        fill(create_template_form, {'template_name': self.template_name,
                                    'description': self.description,
                                    'template_type': temp_type,
                                    'content': content},
            action=create_template_form.add_button)
        flash.assert_success_message('Orchestration Template "%s" was saved' %
                                     self.template_name)

    def update(self, updates):
        sel.force_navigate('edit_template',
                           context={'template_type': self.template_type,
                                    'template_name': self.template_name})
        fill(create_template_form, {'template_name': updates.get('template_name', None),
                                    'description': updates.get('description', None)},
             action=create_template_form.edit_button)
        flash.assert_success_message('Orchestration Template "%s" was saved' %
                                     self.template_name)

    def delete(self):
        sel.force_navigate('select_template',
                           context={'template_type': self.template_type,
                                    'template_name': self.template_name})
        cfg_btn("Remove this Orchestration Template", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Orchestration Template "%s" was deleted.' %
                                     self.template_name)

    def copy_template(self, template_name, content):
        sel.force_navigate('select_template',
                           context={'template_type': self.template_type,
                                    'template_name': self.template_name})
        cfg_btn("Copy this Orchestration Template")
        fill(create_template_form, {'template_name': template_name,
                                    'content': content},
             action=create_template_form.add_button)
        flash.assert_success_message('Orchestration Template "%s" was saved' %
                                     template_name)

    def create_service_dialog(self, dialog_name):
        sel.force_navigate('orch_template_type',
                           context={'template_type': self.template_type})
        if(self.template_type == "CloudFormation Templates"):
            template_name = sel.text("//li[@id='ot_xx-otcfn']/ul"
                "//a[contains(@class, 'dynatree-title')]").encode("utf-8")
        else:
            template_name = sel.text("//li[@id='ot_xx-othot']/ul"
                "//a[contains(@class, 'dynatree-title')]").encode("utf-8")
        sel.force_navigate('create_service_dialog',
                           context={'template_type': self.template_type,
                                    'template_name': template_name})
        fill(dialog_form, {'dialog_name': dialog_name},
             action=dialog_form.save_button)
        flash.assert_success_message('Service Dialog "%s" was successfully created' %
                                     dialog_name)
        return template_name

    def create_service_dialog_from_template(self, dialog_name, template_name):
        sel.force_navigate('orch_template_type',
                           context={'template_type': self.template_type})
        sel.force_navigate('create_service_dialog',
                           context={'template_type': self.template_type,
                                    'template_name': template_name})
        fill(dialog_form, {'dialog_name': dialog_name},
             action=dialog_form.save_button)
        flash.assert_success_message('Service Dialog "%s" was successfully created' %
                                     dialog_name)
        return template_name
