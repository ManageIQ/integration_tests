# -*- coding: utf-8 -*-
from functools import partial
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import accordion, fill, form_buttons, menu, Form, Input, flash
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
                'create_service_dialog': _orch_templates_create_dialog,
                'orch_template_type':
                [
                    lambda ctx: accordion_tree(
                        'All Orchestration Templates', ctx['template_type']),
                    {'create_new_template': lambda _: cfg_btn("Create New Orchestration template")}
                ]
            }
        ]
    }
)


class OrchestrationTemplate(Updateable, Pretty):
    pretty_attrs = ['template_type', 'template_name']

    def __init__(self, template_type=None):
        self.template_type = template_type

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
