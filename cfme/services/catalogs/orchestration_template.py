# -*- coding: utf-8 -*-
from functools import partial
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    accordion, fill, form_buttons, menu, Form, Input, flash, AngularSelect, Select, ScriptBox)
from cfme.web_ui import summary_title, paginator as pg, toolbar as tb
from navmazing import NavigateToAttribute, NavigateToSibling
from utils.update import Updateable
from utils.pretty import Pretty
from utils import error, version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


cfg_btn = partial(tb.select, "Configuration")
accordion_tree = partial(accordion.tree, "Orchestration Templates")

dialog_form = Form(
    fields=[
        ('dialog_name', Input("dialog_name")),
        ('save_button', form_buttons.save)
    ])

create_template_form = Form(
    fields=[
        ('description', "textarea#description"),
        ("template_type", {
            version.LOWEST: Select("select#type"),
            '5.5': AngularSelect('type')}),
        ('content', ScriptBox(ta_locator="//div[@id='basic_info_div']/div/div"
                    "/div/div/div/div/div/div/pre/span")),
        ('template_name', Input("name")),
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


class OrchestrationTemplate(Updateable, Pretty, Navigatable):
    pretty_attrs = ['template_type', 'template_name']

    def __init__(self, template_type=None, template_name=None, description=None,
                 appliance=None):
        Navigatable.__init__(self, appliance)
        self.template_type = template_type
        self.template_name = template_name
        self.description = description

    def create_form(self, content):
        navigate_to(self, "AddTemplate")
        if(self.template_type == "CloudFormation Templates"):
            temp_type = "Amazon CloudFormation"
        else:
            temp_type = "OpenStack Heat"
        fill(create_template_form, {'description': self.description,
                                    'template_type': temp_type,
                                    'content': content,
                                    'template_name': self.template_name},
            action=create_template_form.add_button)

    def create(self, content):
        self.create_form(content)
        try:
            flash.assert_success_message('Orchestration Template "{}" was saved'.format(
                self.template_name))
        except Exception as e:
            if error.match("Error during 'Orchestration Template creation': Validation failed: \
                            Md5 of content already exists (content must be unique)", e):
                self.create_form(content + " ")
            raise

    def update(self, updates):
        navigate_to(self, "Edit")
        fill(create_template_form, {'template_name': updates.get('template_name', None),
                                    'description': updates.get('description', None)},
             action=create_template_form.edit_button)
        flash.assert_success_message('Orchestration Template "{}" was saved'.format(
            self.template_name))

    def delete(self):
        navigate_to(self, "TemplateDetails")
        cfg_btn("Remove this Orchestration Template", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Orchestration Template "{}" was deleted.'.format(
            self.template_name))

    def delete_all_templates(self):
        navigate_to(self, "TemplateType")
        sel.click(pg.check_all())
        cfg_btn("Remove selected Orchestration Templates", invokes_alert=True)
        sel.handle_alert()

    def copy_template(self, template_name, content):
        navigate_to(self, "TemplateDetails")
        cfg_btn("Copy this Orchestration Template")
        fill(create_template_form, {'template_name': template_name,
                                    'content': content},
             action=create_template_form.add_button)
        flash.assert_success_message('Orchestration Template "{}" was saved'.format(
            template_name))

    def create_service_dialog(self, dialog_name):
        navigate_to(self, "TemplateType")
        if(self.template_type == "CloudFormation Templates"):
            template_name = sel.text("//li[@id='ot_xx-otcfn']/ul"
                "//a[contains(@class, 'dynatree-title')]").encode("utf-8")
        else:
            template_name = sel.text("//li[@id='ot_xx-othot']/ul"
                "//a[contains(@class, 'dynatree-title')]").encode("utf-8")
        navigate_to(self, "AddDialog")
        fill(dialog_form, {'dialog_name': dialog_name},
             action=dialog_form.save_button)
        flash.assert_success_message('Service Dialog "{}" was successfully created'.format(
            dialog_name))
        return template_name

    def create_service_dialog_from_template(self, dialog_name, template_name):
        navigate_to(self, "AddDialog")
        fill(dialog_form, {'dialog_name': dialog_name},
             action=dialog_form.save_button)
        flash.assert_success_message('Service Dialog "{}" was successfully created'.format(
            dialog_name))
        return template_name


@navigator.register(OrchestrationTemplate, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Services', 'Catalogs')(None)
        accordion.tree("Orchestration Templates", "All Orchestration Templates")

    def am_i_here(self, *args, **kwargs):
        return summary_title() == "All Orchestration Templates"


@navigator.register(OrchestrationTemplate, 'TemplateDetails')
class TemplateDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion_tree("All Orchestration Templates", self.obj.template_type, self.obj.template_name)


@navigator.register(OrchestrationTemplate, 'TemplateType')
class TemplateType(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion_tree("All Orchestration Templates", self.obj.template_type)


@navigator.register(OrchestrationTemplate, 'AddDialog')
class AddDialog(CFMENavigateStep):
    prerequisite = NavigateToSibling('TemplateDetails')

    def step(self):
        cfg_btn('Create Service Dialog from "Orchestration Template"')


@navigator.register(OrchestrationTemplate, 'Edit')
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('TemplateDetails')

    def step(self):
        cfg_btn("Edit this Orchestration Template")


@navigator.register(OrchestrationTemplate, 'AddTemplate')
class AddTemplate(CFMENavigateStep):
    prerequisite = NavigateToSibling('TemplateType')

    def step(self):
        cfg_btn("Create new Orchestration Template")
