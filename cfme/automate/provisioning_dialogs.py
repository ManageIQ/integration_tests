# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View, Text, TextInput
from widgetastic_patternfly import Dropdown, BootstrapSelect, CandidateNotFound
from widgetastic_manageiq import Button, Table, PaginationPane, SummaryForm, ScriptBox

from cfme.base.login import BaseLoggedInPage
from cfme.base.ui import automate_menu_name
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from . import AutomateCustomizationView

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
        expected_navigation = automate_menu_name(self.context['object'].appliance)
        expected_navigation.append('Customization')
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == expected_navigation)

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
        # FIXME https://github.com/ManageIQ/manageiq-ui-classic/issues/1983
        # 'Editing' should only be in the title once
        expected_title = 'Editing Editing Dialog "{}"'.format(self.context['object'].description)
        return (
            self.in_customization and
            self.title.text == expected_title and
            self.form.is_displayed)

    title = Text('#explorer_title_text')

    @View.nested
    class form(ProvDiagForm):  # noqa
        save = Button('Save')
        reset = Button('Reset')


class ProvisioningDialog(Updateable, Pretty, Navigatable):
    HOST_PROVISION = 'Host Provision'
    VM_MIGRATE = 'VM Migrate'
    VM_PROVISION = 'VM Provision'
    SYSTEM_PROVISION = 'Configured System Provision'
    ALLOWED_TYPES = {HOST_PROVISION, VM_MIGRATE, VM_PROVISION, SYSTEM_PROVISION}

    pretty_attrs = ['name', 'description', 'diag_type', 'content']

    def __init__(self, diag_type, name=None, description=None, content=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.description = description
        self.content = content
        if diag_type in self.ALLOWED_TYPES:
            self.diag_type = diag_type
        else:
            raise TypeError('Type must be one of ProvisioningDialog constants: {}'
                            .format(self.ALLOWED_TYPES))

    def __str__(self):
        return self.name

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
        except CandidateNotFound:
            return False
        return True

    def create(self, cancel=False):
        view = navigate_to(self, 'Add')
        # might not want to use pretty_attrs here, overloading its intended use
        fill_args = {key: self.__dict__[key] for key in self.pretty_attrs}
        view.form.fill(fill_args)
        if cancel:
            flash_msg = 'Add of new Dialog was cancelled by the user'
            btn = view.form.cancel
        else:
            flash_msg = 'Dialog "{}" was added'.format(self.name)
            btn = view.form.add

        btn.click()
        view = self.create_view(ProvDiagAllView if cancel else ProvDiagDetailsView)
        assert view.is_displayed
        view.flash.assert_success_message(flash_msg)

    def update(self, updates, cancel=False, reset=False):
        view = navigate_to(self, 'Edit')
        view.form.fill(updates)
        if reset:
            cancel = True
            view.form.reset.click()
            view.flash.assert_message('All changes have been reset')
        if cancel:
            flash_msg = 'Edit of Dialog "{}" was cancelled by the user'.format(self.name)
            btn = view.form.cancel
        else:
            flash_msg = ('Dialog "{}" was saved'.format(updates.get('name') or self.name))
            btn = view.form.save

        btn.click()
        view = self.create_view(ProvDiagDetailsView)
        # TODO use override in create_view in order to assert view.is_displayed
        # Saw inconsistent UI behavior when trying to use it, where UI was jumping to 'All' view
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


@navigator.register(ProvisioningDialog, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')
    VIEW = ProvDiagAllView

    def step(self):
        self.prerequisite_view.provisioning_dialogs.tree.click_path('All Dialogs')


@navigator.register(ProvisioningDialog, 'Add')
class Add(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = ProvDiagAddView

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Add a new Dialog")


@navigator.register(ProvisioningDialog, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = ProvDiagDetailsView

    def step(self):
        accordion_tree = self.prerequisite_view.sidebar.provisioning_dialogs.tree
        accordion_tree.click_path("All Dialogs", self.obj.diag_type, self.obj.description)


@navigator.register(ProvisioningDialog, 'Edit')
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = ProvDiagEditView

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Edit this Dialog")
