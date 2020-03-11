import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import Checkbox
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from cfme.common import Taggable
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.services.catalogs import ServicesCatalogView
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.version import LOWEST
from cfme.utils.version import VersionPicker
from cfme.utils.wait import wait_for
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import ReactCodeMirror
from widgetastic_manageiq import ReactSelect
from widgetastic_manageiq import ScriptBox
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import Table


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
    template_type = VersionPicker({
        "5.11": ReactSelect("type"),
        LOWEST: BootstrapSelect("type")
    })
    name = Input(name='name')
    description = Input(name="description")
    draft = Checkbox(name='draft')
    content = VersionPicker({
        "5.11": ReactCodeMirror(),
        LOWEST: ScriptBox(locator="//pre[@class=' CodeMirror-line ']/span")
    })


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
            self.title.text == "Editing {}".format(self.context['object'].template_name) and
            self.orchestration_templates.is_opened
        )


class CopyTemplateView(CopyTemplateForm):
    title = Text('#explorer_title_text')
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.title.text == "Copying {}".format(self.context['object'].template_name) and
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
    name = VersionPicker({
        "5.11": Input(name='label'),
        LOWEST: Input(name='dialog_name')
    })


class AddDialogView(DialogForm):

    add_button = Button("Save")

    @property
    def is_displayed(self):
        return (
            self.orchestration_templates.is_opened and
            self.title.text == 'Adding a new Service Dialog from Orchestration Template "{}"'
                               .format(self.context['object'].template_name)
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
        view.flash.wait_displayed("10s")
        if self.appliance.version < "5.11":
            view.flash.assert_success_message(
                f'Orchestration Template "{self.template_name}" was saved')
        else:
            view.flash.assert_success_message(
                f'Orchestration Template {self.template_name} was saved')

    def delete(self):
        view = navigate_to(self, 'Details')
        msg = "Remove this Orchestration Template from Inventory"
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
        view.flash.wait_displayed("10s")
        view.flash.assert_no_error()
        # TODO - Move assertions to tests
        return self.parent.instantiate(template_group=self.template_group,
                                       description=description,
                                       template_name=template_name,
                                       content=content,
                                       draft=draft)

    def create_service_dialog_from_template(self, dialog_name):
        view = navigate_to(self, 'AddDialog')
        view.fill({'name': dialog_name})
        wait_for(lambda: view.add_button.is_enabled, num_sec=5)
        view.add_button.click()
        view.flash.assert_no_error()
        service_dialog = self.parent.parent.collections.service_dialogs.instantiate(
            label=dialog_name)
        return service_dialog


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
        view.flash.wait_displayed("10s")
        view.flash.assert_no_error()
        template = self.instantiate(template_group=template_group, description=description,
                                    template_name=template_name, content=content, draft=draft)
        return template


@navigator.register(OrchestrationTemplatesCollection)
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    VIEW = OrchestrationTemplatesView

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'Catalogs')
        self.view.orchestration_templates.tree.click_path("All Orchestration Templates")


@navigator.register(OrchestrationTemplate)
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')

    VIEW = DetailsTemplateView

    def step(self, *args, **kwargs):
        self.view.orchestration_templates.tree.click_path("All Orchestration Templates",
                                                          self.obj.template_group,
                                                          self.obj.template_name)


@navigator.register(OrchestrationTemplatesCollection)
class TemplateType(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    VIEW = TemplateTypeView

    def step(self, *args, **kwargs):
        self.view.orchestration_templates.tree.click_path("All Orchestration Templates",
                                                          self.obj.template_group)


@navigator.register(OrchestrationTemplate)
class AddDialog(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    VIEW = AddDialogView

    def step(self, *args, **kwargs):
        item_name = 'Create Service Dialog from Orchestration Template'
        self.view.toolbar.configuration.item_select(item_name)


@navigator.register(OrchestrationTemplate)
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    VIEW = EditTemplateView

    def step(self, *args, **kwargs):
        self.view.toolbar.configuration.item_select("Edit this Orchestration Template")


@navigator.register(OrchestrationTemplatesCollection)
class AddTemplate(CFMENavigateStep):
    prerequisite = NavigateToSibling('TemplateType')

    VIEW = AddTemplateView

    def step(self, *args, **kwargs):
        self.view.toolbar.configuration.item_select("Create new Orchestration Template")


@navigator.register(OrchestrationTemplate)
class CopyTemplate(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    VIEW = CopyTemplateView

    def step(self, *args, **kwargs):
        self.view.toolbar.configuration.item_select("Copy this Orchestration Template")
