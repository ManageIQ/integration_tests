# -*- coding: utf-8 -*-
import attr

from widgetastic.widget import View, Text, Checkbox
from widgetastic_patternfly import BootstrapSelect, Button, CandidateNotFound, Input
from widgetastic_manageiq import ScriptBox, Table, PaginationPane, SummaryTable
from navmazing import NavigateToAttribute, NavigateToSibling

from cfme.common import Taggable
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable

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


class TemplateForm(ServicesCatalogView):
    title = Text('#explorer_title_text')
    template_type = BootstrapSelect("type")
    name = Input(name='name')
    description = Input(name="description")
    draft = Checkbox(name='draft')
    content = ScriptBox(locator="//pre[@class=' CodeMirror-line ']/span")


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
            self.title.text == "Editing {}".format(self.context['object'].name) and
            self.orchestration_templates.is_opened
        )


class CopyTemplateView(CopyTemplateForm):
    title = Text('#explorer_title_text')
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.is_displayed and
            self.title.text == "Copying {}".format(self.context['object'].name) and
            self.orchestration_templates.is_opened
        )


class DetailsTemplateEntities(View):
    title = Text('#explorer_title_text')
    smart_management = SummaryTable(title='Smart Management')


class DetailsTemplateView(ServicesCatalogView):
    entities = View.nested(DetailsTemplateEntities)

    @property
    def is_displayed(self):
        """ Removing last 's' character from template_group.
        For ex. 'CloudFormation Templates' ->  'CloudFormation Template'"""
        return (
            self.entities.title.text == '{} "{}"'.format(self.context['object'].template_group[:-1],
                                                self.context['object'].template_name) and
            self.orchestration_templates.is_opened
        )


class TemplateTypeView(ServicesCatalogView):
    title = Text('#explorer_title_text')
    templates = Table("//table[@class='table table-striped table-bordered "
                      "table-hover table-selectable]'")
    paginator = PaginationPane()

    @property
    def is_displayed(self):
        return (
            self.title.text == 'All {}'.format(self.context['object'].template_group) and
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


@attr.s
class OrchestrationTemplate(BaseEntity, Updateable, Pretty, Taggable):

    template_group = attr.ib()
    template_name = attr.ib()
    content = attr.ib()
    description = attr.ib(default=None)
    draft = attr.ib(default=None)

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        view.fill({'description': updates.get('description'),
                   'name': updates.get('template_name'),
                   'draft': updates.get('draft'),
                   'content': updates.get('content')})
        view.save_button.click()
        view.flash.assert_success_message('Orchestration Template "{}" was saved'.format(
            self.template_name))

    def delete(self):
        view = navigate_to(self, 'Details')
        msg = "Remove this Orchestration Template"
        if self.appliance.version >= '5.9':
            msg = '{} from Inventory'.format(msg)
        view.toolbar.configuration.item_select(msg, handle_alert=True)
        view.flash.assert_success_message('Orchestration Template "{}" was deleted.'.format(
            self.template_name))

    def delete_all_templates(self):
        view = navigate_to(self, 'TemplateType')
        view.paginator.check_all()
        view.configuration.item_select("Remove selected Orchestration Templates", handle_alert=True)

    def copy_template(self, template_name, content, draft=None, description=None):
        view = navigate_to(self, 'CopyTemplate')
        view.fill({'name': template_name,
                   'content': content,
                   'draft': draft,
                   'description': description
                   })
        view.add_button.click()
        view.flash.assert_success_message('Orchestration Template "{}" was saved'.format(
            template_name))
        return self.parent.instantiate(template_group=self.template_group,
                                       description=description,
                                       template_name=template_name,
                                       content=content,
                                       draft=draft)

    def create_service_dialog_from_template(self, dialog_name):
        view = navigate_to(self, 'AddDialog')
        view.fill({'name': dialog_name})
        view.add_button.click()
        view.flash.assert_success_message('Service Dialog "{}" was successfully created'.format(
            dialog_name))
        service_dialog = self.parent.parent.collections.service_dialogs.instantiate(
            label=dialog_name)
        return service_dialog

    @property
    def exists(self):
        try:
            navigate_to(self, "Details")
            return True
        except CandidateNotFound:
            return False


@attr.s
class OrchestrationTemplatesCollection(BaseCollection):
    """A collection for the :py:class:`cfme.services.catalogs.orchestration_template`"""
    ENTITY = OrchestrationTemplate

    def create(self, template_name, description, template_group,
               template_type, draft=None, content=None):
        self.template_group = template_group
        view = navigate_to(self, 'AddTemplate')
        view.fill({'name': template_name,
                   'description': description,
                   'template_type': template_type,
                   'draft': draft,
                   'content': content})
        view.add_button.click()
        template = self.instantiate(template_group=template_group, description=description,
                                    template_name=template_name, content=content, draft=draft)
        view = self.create_view(DetailsTemplateView)
        view.flash.assert_success_message('Orchestration Template '
                                          '"{}" was saved'.format(template_name))
        return template


@navigator.register(OrchestrationTemplatesCollection)
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    VIEW = OrchestrationTemplatesView

    def step(self):
        self.prerequisite_view.navigation.select('Services', 'Catalogs')
        self.view.orchestration_templates.tree.click_path("All Orchestration Templates")

    def am_i_here(self, *args, **kwargs):
        return self.view.is_displayed


@navigator.register(OrchestrationTemplate)
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')

    VIEW = DetailsTemplateView

    def step(self):
        self.view.orchestration_templates.tree.click_path("All Orchestration Templates",
                                                          self.obj.template_group,
                                                          self.obj.template_name)

    def am_i_here(self, *args, **kwargs):
        return self.view.is_displayed


@navigator.register(OrchestrationTemplatesCollection)
class TemplateType(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    VIEW = TemplateTypeView

    def step(self):
        self.view.orchestration_templates.tree.click_path("All Orchestration Templates",
                                                          self.obj.template_group)


@navigator.register(OrchestrationTemplate)
class AddDialog(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    VIEW = AddDialogView

    def step(self):
        item_name = 'Create Service Dialog from Orchestration Template'
        self.view.toolbar.configuration.item_select(item_name)


@navigator.register(OrchestrationTemplate)
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    VIEW = EditTemplateView

    def step(self):
        self.view.toolbar.configuration.item_select("Edit this Orchestration Template")


@navigator.register(OrchestrationTemplatesCollection)
class AddTemplate(CFMENavigateStep):
    prerequisite = NavigateToSibling('TemplateType')

    VIEW = AddTemplateView

    def step(self):
        self.view.toolbar.configuration.item_select("Create new Orchestration Template")


@navigator.register(OrchestrationTemplate)
class CopyTemplate(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    VIEW = CopyTemplateView

    def step(self):
        self.view.toolbar.configuration.item_select("Copy this Orchestration Template")
