from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text
from widgetastic_manageiq import SSUIlist, SSUIDropdown, SSUIAppendToBodyDropdown
from widgetastic_patternfly import Input, Button

from cfme.base.ssui import SSUIBaseLoggedInPage
from cfme.common.vm import VM
from cfme.utils.appliance.implementations.ssui import (
    navigator,
    SSUINavigateStep,
    navigate_to,
    ViaSSUI
)
from cfme.utils.wait import wait_for

from . import MyService


class MyServicesView(SSUIBaseLoggedInPage):
    title = Text(locator='//li[@class="active"]')
    service = SSUIlist(list_name='serviceList')

    def in_myservices(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["", "My Services"])

    @property
    def is_displayed(self):
        return self.in_myservices and self.title.text == "My Services"


class DetailsMyServiceView(MyServicesView):
    title = Text(locator='//li[@class="active"]')

    @property
    def is_displayed(self):
        return (self.in_myservices and
               self.title.text in {self.context['object'].name, 'Service Details'})

    configuration = SSUIDropdown('Configuration')
    policy_btn = SSUIDropdown('Policy')
    lifecycle_btn = SSUIDropdown('Lifecycle')
    power_operations = SSUIDropdown('Power Operations')
    access_dropdown = SSUIAppendToBodyDropdown('Access')


class ServiceEditForm(MyServicesView):
    title = Text(locator='//li[@class="active"]')

    name = Input(name='name')
    description = Input(name='description')


class EditMyServiceView(ServiceEditForm):
    title = Text(locator='//li[@class="active"]')

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.title.text == "Edit Service"
        )


@MyService.update.external_implementation_for(ViaSSUI)
def update(self, updates):
    view = navigate_to(self, 'Edit')
    view.fill_with(updates, on_change=view.save_button, no_change=view.cancel_button)
    view.flash.assert_no_error()
    view = self.create_view(DetailsMyServiceView, override=updates)
    wait_for(
        lambda: view.is_displayed, delay=15, num_sec=300,
        message="waiting for view to be displayed"
    )
    # TODO - implement notifications and then assert.


@MyService.launch_vm_console.external_implementation_for(ViaSSUI)
def launch_vm_console(self, catalog_item):
    navigate_to(self, 'VM Console')
    # TODO need to remove 0001 from the line below and find correct place/way to put it in code
    vm_obj = VM.factory(catalog_item.provisioning_data['catalog']['vm_name'] + '0001',
                catalog_item.provider, template_name=catalog_item.catalog_name)
    wait_for(
        func=lambda: vm_obj.vm_console, num_sec=30, delay=2, handle_exception=True,
        message="waiting for VM Console window to open"
    )
    return vm_obj.vm_console


@navigator.register(MyService, 'All')
class MyServiceAll(SSUINavigateStep):
    VIEW = MyServicesView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('My Services')


@navigator.register(MyService, 'Details')
class Details(SSUINavigateStep):
    VIEW = DetailsMyServiceView

    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.service.click_at(self.obj.name)


@navigator.register(MyService, 'Edit')
class MyServiceEdit(SSUINavigateStep):
    VIEW = EditMyServiceView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit')


@navigator.register(MyService, 'VM Console')
class LaunchVMConsole(SSUINavigateStep):
    VIEW = EditMyServiceView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.access_dropdown.item_select('VM Console')
