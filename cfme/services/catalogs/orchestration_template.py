# -*- coding: utf-8 -*-
from widgetastic.widget import Text, Checkbox
from widgetastic_patternfly import BootstrapSelect, Button, Input
from widgetastic_manageiq import ScriptBox, Table
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import paginator as pg
from navmazing import NavigateToAttribute, NavigateToSibling
from utils.update import Updateable
from utils.pretty import Pretty
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


from . import ServicesCatalogView


class OrchestrationTemplatesView(ServicesCatalogView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            super(OrchestrationTemplatesView, self).is_displayed and
            self.title.text == 'All Orchestration Templates' and
            self.orchestration_templates.is_opened and
            self.orchestration_templates.tree.currently_selected == ["All Orchestration Templates"])


class CopyTemplateForm(ServicesCatalogView):
    title = Text('#explorer_title_text')

    name = Input(name='name')
    description = Input(name="description")
    draft = Checkbox(name='draft')
    content = ScriptBox(locator="//pre[@class=' CodeMirror-line ']/span")

    cancel_button = Button('Cancel')


class TemplateForm(CopyTemplateForm):

    template_type = BootstrapSelect("type")


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


class DetailsTemplateView(ServicesCatalogView):

    @property
    def is_displayed(self):
        """ Removing last 's' character from template_type.
        For ex. 'CloudFormation Templates' ->  'CloudFormation Template'"""
        return (
            self.title.text == '{} "{}"'.format(self.obj.template_type[:-1],
                                                self.obj.template_name) and
            self.orchestration_templates.is_opened
        )


class TemplateTypeView(ServicesCatalogView):

    templates = Table("//table[@class='table table-striped table-bordered "
                      "table-hover table-selectable]'")

    @property
    def is_displayed(self):
        return (
            self.title.text == 'All {}'.format(self.obj.template_type) and
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
                 draft=None, content=None, appliance=None):
        Navigatable.__init__(self, appliance)
        self.template_type = template_type
        self.template_name = template_name
        self.description = description
        self.draft = draft
        self.content = content

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
        view.flash.assert_success_message('Orchestration Template '
                                  '"{}" was saved'.format(self.template_name))

    def update(self, updates):
        view = navigate_to(self, "Edit")
        view.fill({'description': updates.get('description', None),
                   'name': updates.get('template_name', None),
                   'draft': updates.get('draft', None),
                   'content': updates.get('content', None)})
        view.save_button.click()
        view.flash.assert_success_message('Orchestration Template "{}" was saved'.format(
            self.template_name))

    def delete(self):
        view = navigate_to(self, "Details")
        view.configuration.item_select("Remove this Orchestration Template", handle_alert=True)
        view.flash.assert_success_message('Orchestration Template "{}" was deleted.'.format(
            self.template_name))

    def delete_all_templates(self):
        view = navigate_to(self, "TemplateType")
        sel.click(pg.check_all())
        view.configuration.item_select("Remove selected Orchestration Templates", handle_alert=True)

    def copy_template(self, template_name, content, draft=None, description=None):
        view = navigate_to(self, "CopyTemplate")
        view.fill({'name': template_name,
                   'content': content,
                   'draft': draft,
                   'description': description
                   })
        view.add_button.click()
        view.flash.assert_success_message('Orchestration Template "{}" was saved'.format(
            template_name))

    def create_service_dialog_from_template(self, dialog_name, template_name):
        view = navigate_to(self, "AddDialog")
        view.fill({'name': dialog_name})
        view.add_button.click()
        view.flash.assert_success_message('Service Dialog "{}" was successfully created'.format(
            dialog_name))
        return template_name


@navigator.register(OrchestrationTemplate, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    VIEW = OrchestrationTemplatesView

    def step(self):
        self.prerequisite_view.navigation.select('Services', 'Catalogs')
        self.view.orchestration_templates.tree.click_path("All Orchestration Templates")

    def am_i_here(self, *args, **kwargs):
        return self.view.is_displayed


@navigator.register(OrchestrationTemplate, 'Details')
class Details(CFMENavigateStep):
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
    prerequisite = NavigateToSibling('Details')

    VIEW = AddDialogView

    def step(self):
        self.view.configuration.item_select('Create Service Dialog from Orchestration Template')


@navigator.register(OrchestrationTemplate, 'Edit')
class EditTemplate(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

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
    prerequisite = NavigateToSibling('Details')

    VIEW = CopyTemplateView

    def step(self):
        self.view.configuration.item_select("Copy this Orchestration Template")
