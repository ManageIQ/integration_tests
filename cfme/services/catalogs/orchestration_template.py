# -*- coding: utf-8 -*-
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import paginator as pg
from navmazing import NavigateToAttribute, NavigateToSibling
from utils.update import Updateable
from utils.pretty import Pretty
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from widgetastic.widget import Text, Checkbox
from widgetastic_patternfly import BootstrapSelect, Button, Input
from widgetastic_manageiq import ScriptBox

from . import ServicesCatalogView


class OrchestrationTemplatesAllView(ServicesCatalogView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            super(OrchestrationTemplatesAllView, self).is_displayed and
            self.title.text == 'All Orchestration Templates' and
            self.orchestration_templates.is_opened and
            self.orchestration_templates.tree.currently_selected == ["All Orchestration Templates"])


class TemplateForm(ServicesCatalogView):
    title = Text('#explorer_title_text')

    name = Input(name='name')
    description = Input(name="description")
    template_type = BootstrapSelect("type")
    draft = Checkbox(name='draft')
    content = ScriptBox(locator="//div[@id='basic_info_div']/div/div"
                    "/div/div/div/div/div/div/pre/span")

    cancel_button = Button('Cancel')


class CopyTemplateForm(ServicesCatalogView):
    title = Text('#explorer_title_text')

    name = Input(name='name')
    description = Input(name="description")
    draft = Checkbox(name='draft')
    content = ScriptBox(locator="//div[@id='basic_info_div']/div/div"
                    "/div/div/div/div/div/div/pre/span")

    cancel_button = Button('Cancel')


class AddTemplateView(TemplateForm):

    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.title.text == "Adding a new Orchestration Template" and
            self.orchestration_templates.is_opened
        )


class EditTemplateView(TemplateForm):

    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.title.text == "Editing {}".format(self.obj.name) and
            self.orchestration_templates.is_opened
        )


class CopyTemplateView(CopyTemplateForm):

    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.is_displayed and
            self.title.text == "Copying {}".format(self.obj.name) and
            self.orchestration_templates.is_opened
        )


class DetailsTemplateView(TemplateForm):

    @property
    def is_displayed(self):
        return (
            self.title.text == '{} "{}"'.format(self.obj.template_type[:-1],
                                                self.obj.template_name) and
            self.orchestration_templates.is_opened
        )


class TemplateTypeView(TemplateForm):

    @property
    def is_displayed(self):
        return (
            self.title.text == '{} "{}"'.format(self.obj.template_type) and
            self.orchestration_templates.is_opened
        )


class DialogForm(ServicesCatalogView):
    title = Text('#explorer_title_text')

    name = Input(name='dialog_name')


class AddDialogView(DialogForm):

    add_button = Button("Save")

    @property
    def is_displayed(self):
        return (
            self.title.text == 'Adding a new Service Dialog from '
                               'Orchestration Template "{}"'.format(self.obj.name) and
            self.orchestration_templates.is_opened
        )


class OrchestrationTemplate(Updateable, Pretty, Navigatable):

    def __init__(self, template_type=None, template_name=None, description=None,
                 appliance=None):
        Navigatable.__init__(self, appliance)
        self.template_type = template_type
        self.template_name = template_name
        self.description = description

    def create(self, content):
        view = navigate_to(self, "AddTemplate")
        if(self.template_type == "CloudFormation Templates"):
            temp_type = "Amazon CloudFormation"
        else:
            temp_type = "OpenStack Heat"
        view.fill({'name': self.template_name,
                   'description': self.description,
                   'template_type': temp_type,
                   'content': content})
        view.add_button.click()
        view.flash.assert_no_error()
        view.flash.assert_message('Orchestration Template '
                                  '"{}" was saved'.format(self.template_name))

    def update(self, updates):
        view = navigate_to(self, "Edit")
        view.fill({'description': updates.get('description', None),
                   'name': updates.get('template_name', None)})
        view.save_button.click()
        view.flash.assert_message('Orchestration Template "{}" was saved'.format(
            self.template_name))

    def delete(self):
        view = navigate_to(self, "TemplateDetails")
        view.configuration.item_select("Remove this Orchestration Template", handle_alert=True)
        view.flash.assert_message('Orchestration Template "{}" was deleted.'.format(
            self.template_name))

    def delete_all_templates(self):
        view = navigate_to(self, "TemplateType")
        sel.click(pg.check_all())
        view.configuration.item_select("Remove selected Orchestration Templates", handle_alert=True)

    def copy_template(self, template_name, content):
        view = navigate_to(self, "CopyTemplate")
        view.fill({'name': template_name,
                   'content': content
                   })
        view.add_button.click()
        view.flash.assert_message('Orchestration Template "{}" was saved'.format(
            template_name))

    def create_service_dialog(self, dialog_name):
        navigate_to(self, "TemplateType")
        if(self.template_type == "CloudFormation Templates"):
            template_name = sel.text("//li[@id='ot_xx-otcfn']/ul"
                "//a[contains(@class, 'dynatree-title')]").encode("utf-8")
        else:
            template_name = sel.text("//li[@id='ot_xx-othot']/ul"
                "//a[contains(@class, 'dynatree-title')]").encode("utf-8")
        view = navigate_to(self, "AddDialog")
        view.fill({'name': dialog_name})
        view.add_button.click()
        view.flash.assert_message('Service Dialog "{}" was successfully created'.format(
            dialog_name))
        return template_name

    def create_service_dialog_from_template(self, dialog_name, template_name):
        view = navigate_to(self, "AddDialog")
        view.fill({'name': dialog_name})
        view.add_button.click()
        view.flash.assert_message('Service Dialog "{}" was successfully created'.format(
            dialog_name))
        return template_name


@navigator.register(OrchestrationTemplate, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    VIEW = OrchestrationTemplatesAllView

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Services', 'Catalogs')(None)
        self.view.orchestration_templates.tree.click_path("All Orchestration Templates")

    def am_i_here(self, *args, **kwargs):
        return self.view.is_displayed


@navigator.register(OrchestrationTemplate, 'TemplateDetails')
class TemplateDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    VIEW = DetailsTemplateView

    def step(self):
        self.view.orchestration_templates.tree.click_path("All Orchestration Templates",
                                                    self.obj.template_type, self.obj.template_name)

    def am_i_here(self, *args, **kwargs):
        return self.view.is_displayed


@navigator.register(OrchestrationTemplate, 'TemplateType')
class TemplateType(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    VIEW = TemplateTypeView

    def step(self):
        self.view.orchestration_templates.tree.click_path("All Orchestration Templates",
                                                          self.obj.template_type)


@navigator.register(OrchestrationTemplate, 'AddDialog')
class AddDialog(CFMENavigateStep):
    prerequisite = NavigateToSibling('TemplateDetails')

    VIEW = AddDialogView

    def step(self):
        self.view.configuration.item_select('Create Service Dialog from "Orchestration Template"')


@navigator.register(OrchestrationTemplate, 'Edit')
class EditTemplate(CFMENavigateStep):
    prerequisite = NavigateToSibling('TemplateDetails')

    VIEW = EditTemplateView

    def step(self):
        self.view.configuration.item_select("Edit this Orchestration Template")


@navigator.register(OrchestrationTemplate, 'AddTemplate')
class AddTemplate(CFMENavigateStep):
    prerequisite = NavigateToSibling('TemplateType')

    VIEW = AddTemplateView

    def step(self):
        self.view.configuration.item_select("Create new Orchestration Template")


@navigator.register(OrchestrationTemplate, 'CopyTemplate')
class CopyTemplate(CFMENavigateStep):
    prerequisite = NavigateToSibling('TemplateDetails')

    VIEW = CopyTemplateView

    def step(self):
        self.view.configuration.item_select("Copy this Orchestration Template")
