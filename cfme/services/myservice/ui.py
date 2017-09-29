from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, View
from widgetastic_manageiq import (Accordion, ManageIQTree, Calendar, SummaryTable,
                                  BaseNonInteractiveEntitiesView)
from widgetastic_patternfly import Input, BootstrapSelect, Dropdown, Button, CandidateNotFound, Tab

from cfme.base.login import BaseLoggedInPage
from cfme.common import TagPageView
from cfme.common.vm_views import VMDetailsEntities
from cfme.services.myservice import MyService
from cfme.services.requests import RequestsView
from cfme.utils.appliance import current_appliance
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to, ViaUI
from cfme.utils.wait import wait_for


class MyServicesView(BaseLoggedInPage):
    def in_myservices(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Services', 'MyServices'])

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.configuration.is_displayed and not
            self.myservice.is_dimmed)

    @View.nested
    class myservice(Accordion):  # noqa
        ACCORDION_NAME = "Services"

        tree = ManageIQTree()

    # TODO drop '_btn' suffix
    reload = Button(title='Reload current display')
    configuration = Dropdown('Configuration')
    policy_btn = Dropdown('Policy')
    lifecycle_btn = Dropdown('Lifecycle')
    download_choice = Dropdown('Download')


class ServiceRetirementForm(MyServicesView):
    title = Text('#explorer_title_text')

    retirement_date = Calendar('retirementDate')
    retirement_warning = BootstrapSelect('retirement_warn')


class ServiceEditForm(MyServicesView):
    title = Text('#explorer_title_text')

    name = Input(name='name')
    description = Input(name='description')


class SetOwnershipForm(MyServicesView):
    title = Text('#explorer_title_text')

    select_owner = BootstrapSelect('user_name')
    select_group = BootstrapSelect('group_name')


class MyServiceDetailsToolbar(View):
    """View of toolbar widgets to nest"""
    reload = Button(title='Reload current display')


class MyServiceDetailView(MyServicesView):
    title = Text("#explorer_title_text")
    toolbar = View.nested(MyServiceDetailsToolbar)
    entities = View.nested(BaseNonInteractiveEntitiesView)

    @View.nested
    class details(Tab):  # noqa
        properties = SummaryTable(title='Properties')
        lifecycle = SummaryTable(title='Lifecycle')
        relationships = SummaryTable(title='Relationships')
        vm = SummaryTable(title='Totals for Service VMs ')
        smart_mgmt = SummaryTable(title='Smart Management')

    @View.nested
    class provisioning(Tab):  # noqa
        results = SummaryTable(title='Results')
        plays = SummaryTable(title='Plays')
        details = SummaryTable(title='Details')
        credentials = SummaryTable(title='Credentials')
        standart_output = Text('.//div[@id="provisioning"]//pre')

    @View.nested
    class retirement(Tab):  # noqa
        results = SummaryTable(title='Results')
        plays = SummaryTable(title='Plays')
        details = SummaryTable(title='Details')
        credentials = SummaryTable(title='Credentials')
        standart_output = Text('.//div[@id="provisioning"]//pre')

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.myservice.is_opened and
            self.title.text == 'Service "{}"'.format(self.context['object'].name))


class EditMyServiceView(ServiceEditForm):
    title = Text("#explorer_title_text")

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.myservice.is_opened and
            self.title.text == 'Editing Service "{}"'.format(self.context['object'].name)
        )


class SetOwnershipView(SetOwnershipForm):
    title = Text("#explorer_title_text")

    save_button = Button('Save')

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.myservice.is_opened and
            self.title.text == 'Set Ownership of Service "{}"'.format(self.context['object'].name))


class ServiceRetirementView(ServiceRetirementForm):
    title = Text("#explorer_title_text")

    save_button = Button('Save')

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.myservice.is_opened and
            self.myservice.tree.currently_selected == self.context['object'].name and
            self.title.text == 'Set/Remove retirement date for Service')


class ReconfigureServiceView(SetOwnershipForm):
    title = Text("#explorer_title_text")

    submit_button = Button('Submit')

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.myservice.is_opened and
            self.title.text == 'Reconfigure Service "{}"'.format(self.context['object'].name)
        )


class ServiceVMDetailsView(VMDetailsEntities):
    @property
    def is_displayed(self):
        return (
            self.in_myservices and self.myservice.is_opened and
            self.title.text == 'VM and Instance "{}"'.format(self.context['object'].name)
        )


@MyService.retire.external_implementation_for(ViaUI)
def retire(self):
    view = navigate_to(self, 'Details')
    view.lifecycle_btn.item_select("Retire this Service", handle_alert=True)
    view.flash.assert_no_error()
    if self.appliance.version < '5.8':
        view.flash.assert_success_message(
            'Retirement initiated for 1 Service from the {} Database'.format(
                current_appliance.product_name))
    # wait for service to retire
    wait_for(
        lambda: view.details.lifecycle.get_text_of("Retirement State") == 'Retired',
        fail_func=view.toolbar.reload.click,
        num_sec=10 * 60, delay=3,
        message='Service Retirement wait')


@MyService.retire_on_date.external_implementation_for(ViaUI)
def retire_on_date(self, retirement_date):
    view = navigate_to(self, 'SetRetirement')
    view.retirement_date.fill(retirement_date)
    view.save_button.click()
    view = navigate_to(self, 'Details')
    wait_for(
        lambda: view.details.lifecycle.get_text_of("Retirement State") == 'Retired',
        fail_func=view.toolbar.reload.click,
        num_sec=10 * 60, delay=3,
        message='Service Retirement wait')


@MyService.update.external_implementation_for(ViaUI)
def update(self, updates):
    view = navigate_to(self, 'Edit')
    changed = view.fill_with(updates, on_change=view.save_button, no_change=view.cancel_button)
    view.flash.assert_no_error()
    if changed:
        view.flash.assert_success_message(
            'Service "{}" was saved'.format(updates.get('name', self.name)))
    else:
        view.flash.assert_success_message(
            'Edit of Service "{}" was cancelled by the user'.format(
                updates.get('description', self.description)))
    view = self.create_view(MyServiceDetailView, override=updates)
    assert view.is_displayed


@MyService.exists.external_implementation_for(ViaUI)
def exists(self):
    try:
        navigate_to(self, 'Details')
        return True
    except CandidateNotFound:
        return False


@MyService.delete.external_implementation_for(ViaUI)
def delete(self):
    view = navigate_to(self, 'Details')
    view.configuration.item_select('Remove Service', handle_alert=True)
    view = self.create_view(MyServicesView)
    view.flash.assert_no_error()
    assert view.is_displayed
    view.flash.assert_success_message(
        'Service "{}": Delete successful'.format(self.name))


@MyService.set_ownership.external_implementation_for(ViaUI)
def set_ownership(self, owner, group):
    view = navigate_to(self, 'SetOwnership')
    view.fill({'select_owner': owner,
               'select_group': group})
    view.save_button.click()
    view = self.create_view(MyServiceDetailView)
    assert view.is_displayed
    view.flash.assert_no_error()
    view.flash.assert_success_message('Ownership saved for selected Service')


@MyService.edit_tags.external_implementation_for(ViaUI)
def edit_tags(self, tag, value):
    view = navigate_to(self, 'EditTagsFromDetails')
    view.fill({'select_tag': tag,
               'select_value': value})
    view.save_button.click()
    view = self.create_view(MyServiceDetailView)
    assert view.is_displayed
    view.flash.assert_no_error()
    view.flash.assert_success_message('Tag edits were successfully saved')


@MyService.check_vm_add.external_implementation_for(ViaUI)
def check_vm_add(self, add_vm_name):
    view = navigate_to(self, 'Details')
    view.entities.get_entity(add_vm_name).click()
    view.flash.assert_no_error()


@MyService.download_file.external_implementation_for(ViaUI)
def download_file(self, extension):
    view = navigate_to(self, 'All')
    view.download_choice.item_select("Download as {}".format(extension))
    view.flash.assert_no_error()


@MyService.reconfigure_service.external_implementation_for(ViaUI)
def reconfigure_service(self):
    view = navigate_to(self, 'Reconfigure')
    view.submit_button.click()
    view = self.create_view(RequestsView)
    assert view.is_displayed
    view.flash.assert_no_error()


@navigator.register(MyService, 'All')
class MyServiceAll(CFMENavigateStep):
    VIEW = MyServicesView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'My Services')


@navigator.register(MyService, 'Details')
class MyServiceDetails(CFMENavigateStep):
    VIEW = MyServiceDetailView

    prerequisite = NavigateToSibling('All')

    def step(self):
        path_start = "Active Services" if self.appliance.version > '5.8' else "All Services"
        self.prerequisite_view.myservice.tree.click_path(path_start, self.obj.name)


@navigator.register(MyService, 'Edit')
class MyServiceEdit(CFMENavigateStep):
    VIEW = EditMyServiceView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this Service')


@navigator.register(MyService, 'SetOwnership')
class MyServiceSetOwnership(CFMENavigateStep):
    VIEW = SetOwnershipView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Set Ownership')


@navigator.register(MyService, 'EditTagsFromDetails')
class MyServiceEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.policy_btn.item_select('Edit Tags')


@navigator.register(MyService, 'SetRetirement')
class MyServiceSetRetirement(CFMENavigateStep):
    VIEW = ServiceRetirementView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        if self.appliance.version < '5.8':
            self.prerequisite_view.lifecycle_btn.item_select('Set Retirement Date')
        else:
            self.prerequisite_view.lifecycle_btn.item_select(
                'Set Retirement Dates for this Service')


@navigator.register(MyService, 'Reconfigure')
class MyServiceReconfigure(CFMENavigateStep):
    VIEW = ReconfigureServiceView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Reconfigure this Service')


@navigator.register(MyService, 'VMDetails')
class MyServiceVMDetails(CFMENavigateStep):
    VIEW = ServiceVMDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.get_entity(self.obj.vm_name).click()
