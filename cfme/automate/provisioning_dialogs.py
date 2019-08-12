# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import Text
from widgetastic.widget import TextInput
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Dropdown

from cfme.automate import AutomateCustomizationView
from cfme.common import BaseLoggedInPage
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from widgetastic_manageiq import Button
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import ScriptBox
from widgetastic_manageiq import SummaryForm
from widgetastic_manageiq import Table

group_title = 'Basic Information'


class ProvDiagAllToolbar(View):
    """Toolbar with singular configuration dropdown"""
    configuration = Dropdown('Configuration')


class ProvDiagAllEntities(View):
    """All entities view - no view selector, not using BaseEntitiesView"""
    title = Text('#explorer_title_text')
    table = Table("//div[@id='records_div']//table|//div[@class='miq-data-table']//table")
    paginator = PaginationPane()


class ProvDiagDetailsEntities(View):
    """Entities for details page"""
    title = Text('#explorer_title_text')
    basic_info = SummaryForm(group_title=group_title)
    content = ScriptBox('//textarea[contains(@id, "script_data")]')


class ProvDiagForm(View):
    """Base form with common widgets for add and edit"""
    name = TextInput('name')
    description = TextInput('description')
    diag_type = BootstrapSelect(id='dialog_type')
    content = ScriptBox('//textarea[contains(@id, "content_data")]')
    cancel = Button('Cancel')


class ProvDiagView(BaseLoggedInPage):
    @property
    def in_customization(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Automation", "Automate", "Customization"]
        )

    # sidebar are the same on all, details, etc
    sidebar = View.nested(AutomateCustomizationView)


class ProvDiagAllView(ProvDiagView):
    @property
    def is_displayed(self):
        return (
            self.in_customization and
            self.entities.title.text == 'All Dialogs')

    toolbar = View.nested(ProvDiagAllToolbar)
    entities = View.nested(ProvDiagAllEntities)


class ProvDiagDetailsView(ProvDiagView):
    @property
    def is_displayed(self):
        # FIXME https://github.com/ManageIQ/manageiq-ui-classic/issues/1983
        # 'Editing' should NOT be in the title here
        expected_title = 'Editing Dialog "{}"'.format(self.context['object'].description)
        basic_info_widget = self.entities.basic_info
        return (
            self.in_customization and
            self.entities.title.text == expected_title and
            basic_info_widget.get_text_of('Name') == self.context['object'].name and
            basic_info_widget.get_text_of('Description') == self.context['object'].description)

    toolbar = View.nested(ProvDiagAllToolbar)
    entities = View.nested(ProvDiagDetailsEntities)


class ProvDiagAddView(ProvDiagView):
    @property
    def is_displayed(self):
        return (
            self.in_customization and
            self.title.text == 'Adding a new Dialog' and
            self.form.is_displayed)

    title = Text('#explorer_title_text')

    @View.nested
    class form(ProvDiagForm):  # noqa
        add = Button('Add')


class ProvDiagEditView(ProvDiagView):
    @property
    def is_displayed(self):
        expected_title = 'Editing Dialog "{}"'.format(self.context['object'].description)
        return (
            self.in_customization and
            self.title.text == expected_title and
            self.form.is_displayed and
            self.form.save.is_displayed)

    title = Text('#explorer_title_text')

    @View.nested
    class form(ProvDiagForm):  # noqa
        save = Button('Save')
        reset = Button('Reset')


@attr.s
class ProvisioningDialog(Updateable, Pretty, BaseEntity):
    pretty_attrs = ['name', 'description', 'diag_type', 'content']

    diag_type = attr.ib(default=None)
    name = attr.ib(default=None)
    description = attr.ib(default=None)
    content = attr.ib(default=None)

    @diag_type.validator
    def _validate(self, attribute, value):
        if value not in self.parent.ALLOWED_TYPES:
            raise TypeError('Type must be one of ProvisioningDialog constants: {}'
                            .format(self.parent.ALLOWED_TYPES))

    def __str__(self):
        return str(self.name)

    def update(self, updates, cancel=False, reset=False):
        view = navigate_to(self, 'Edit')
        view.form.fill(updates)
        if reset:
            flash_msg = 'All changes have been reset'
            btn = view.form.reset
            view = self.create_view(ProvDiagDetailsView)
        if cancel:
            flash_msg = 'Edit of Dialog "{}" was cancelled by the user'.format(self.description)
            btn = view.form.cancel
            view = self.create_view(ProvDiagDetailsView)
        else:
            flash_msg = ('Dialog "{}" was saved'.format(updates.get('description') or
                                                        self.description))
            btn = view.form.save
            view = self.create_view(ProvDiagDetailsView, override=updates)
        btn.click()
        assert view.is_displayed
        view.flash.assert_success_message(flash_msg)

    def delete(self, cancel=False):
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove Dialog', handle_alert=(not cancel))

        view = self.create_view(ProvDiagDetailsView if cancel else ProvDiagAllView)
        if cancel:
            assert view.is_displayed
        else:
            # redirects to the type folder, not 'All'
            assert view.sidebar.provisioning_dialogs.tree.selected_item.text == self.diag_type


@attr.s
class ProvisioningDialogsCollection(BaseCollection):
    ENTITY = ProvisioningDialog
    HOST_PROVISION = 'Host Provision'
    VM_MIGRATE = 'VM Migrate'
    VM_PROVISION = 'VM Provision'
    SYSTEM_PROVISION = 'Configured System Provision'
    ALLOWED_TYPES = {HOST_PROVISION, VM_MIGRATE, VM_PROVISION, SYSTEM_PROVISION}

    def create(self, diag_type=None, name=None, description=None, content=None, cancel=False):
        view = navigate_to(self, 'Add')
        dialog = self.instantiate(diag_type=diag_type, name=name, description=description,
                                  content=content)
        view.form.fill({
            'name': dialog.name,
            'description': dialog.description,
            'diag_type': dialog.diag_type,
            'content': dialog.content
        })
        if cancel:
            flash_msg = 'Add of new Dialog was cancelled by the user'
            btn = view.form.cancel
        else:
            flash_msg = 'Dialog "{}" was added'.format(dialog.description)
            btn = view.form.add
        btn.click()
        view = dialog.create_view(ProvDiagAllView if cancel else ProvDiagDetailsView, wait='10s')
        view.flash.assert_success_message(flash_msg)
        return dialog


@navigator.register(ProvisioningDialogsCollection, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')
    VIEW = ProvDiagAllView

    def step(self, *args, **kwargs):
        self.prerequisite_view.provisioning_dialogs.tree.click_path('All Dialogs')


@navigator.register(ProvisioningDialogsCollection, 'Add')
class Add(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = ProvDiagAddView

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select("Add a new Dialog")


@navigator.register(ProvisioningDialog, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = ProvDiagDetailsView

    def step(self, *args, **kwargs):
        accordion_tree = self.prerequisite_view.sidebar.provisioning_dialogs.tree
        accordion_tree.click_path("All Dialogs", self.obj.diag_type, self.obj.description)


@navigator.register(ProvisioningDialog, 'Edit')
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = ProvDiagEditView

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select("Edit this Dialog")
