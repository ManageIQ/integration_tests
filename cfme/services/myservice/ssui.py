from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, Select
from widgetastic_manageiq import (
    SSUIlist,
    SSUIDropdown,
    Notification,
    SSUIAppendToBodyDropdown,
    SSUIConfigDropdown)
from widgetastic_patternfly import Input, Button
from widgetastic.utils import VersionPick, Version

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
# TO DO - remove sleep when BZ 1496233 is fixed
import time


class MyServicesView(SSUIBaseLoggedInPage):
    title = Text(locator='//li[@class="active"]')
    service = SSUIlist(list_name='serviceList')
    notification = Notification()

    @property
    def in_myservices(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["", "My Services"])

    @property
    def is_displayed(self):
        if self.browser.product_version >= '5.8':
            return self.in_myservices and self.title.text == "My Services"
        else:
            return self.in_myservices


class DetailsMyServiceView(MyServicesView):
    title = Text(locator='//li[@class="active"]')

    @property
    def is_displayed(self):
        return (self.in_myservices and
                self.title.text in {self.context['object'].name, 'Service Details'})

    notification = Notification()
    policy_btn = SSUIDropdown('Policy')
    lifecycle_btn = SSUIDropdown('Lifecycle')
    power_operations = SSUIDropdown('Power Operations')
    access_dropdown = SSUIAppendToBodyDropdown('Access')
    remove_service = Button("Remove Service")
    configuration = VersionPick({
        Version.lowest(): SSUIConfigDropdown("dropdownKebabRight"),
        '5.8': SSUIDropdown('Configuration')})


class ServiceEditForm(MyServicesView):
    title = Text(locator='//li[@class="active"]')

    name = Input(name='name')
    description = Input(name='description')


class SetOwnershipForm(MyServicesView):

    select_owner = Select(
        locator='.//select[../../../label[normalize-space(text())="Select an Owner"]]')
    select_group = Select(
        locator='.//select[../../../label[normalize-space(text())="Select a Group"]]')


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


class SetOwnershipView(SetOwnershipForm):
    title = Text(locator='//h4[@id="myModalLabel"]')

    save_button = Button('Save')

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.title.text == 'Set Service Ownership')


class TagForm(MyServicesView):

    tag_category = Select(locator='.//select[contains(@class, "tag-category-select")]')
    tag_name = Select(locator='.//select[contains(@class, "tag-value-select")]')
    add_tag = Text(locator='.//a/span[contains(@class, "tag-add")]')
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


class TagPageView(TagForm):
    title = Text(locator='//h4[@id="myModalLabel"]')

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.title.text == 'Edit Tags')


class RemoveServiceView(MyServicesView):
    title = Text(locator='//h4[@id="myModalLabel"]')

    remove = Button('Yes, Remove Service')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.title.text == 'Remove Service')


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
    # TODO - remove sleep when BZ 1496233 is fixed
    time.sleep(10)
    assert view.notification.assert_message(
        "{} was edited.".format(self.name))


@MyService.set_ownership.external_implementation_for(ViaSSUI)
def set_ownership(self, owner, group):
    view = navigate_to(self, 'SetOwnership')
    wait_for(
        lambda: view.select_owner.is_displayed, delay=5, num_sec=300,
        message="waiting for view to be displayed"
    )
    view.fill({'select_owner': owner,
               'select_group': group})
    view.save_button.click()
    view = self.create_view(DetailsMyServiceView)
    assert view.is_displayed
    # TODO - remove sleep when BZ 1496233 is fixed
    time.sleep(10)
    if self.appliance.version >= "5.8":
        assert view.notification.assert_message("Setting ownership.")
    else:
        assert view.notification.assert_message("{} ownership was saved."
                                                .format(self.name))


@MyService.edit_tags.external_implementation_for(ViaSSUI)
def edit_tags(self, tag, value):
    view = navigate_to(self, 'EditTagsFromDetails')
    wait_for(
        lambda: view.tag_category.is_displayed, delay=15, num_sec=300,
        message="waiting for view to be displayed"
    )
    view.fill({'tag_category': tag,
               'tag_name': value})
    view.add_tag.click()
    view.save.click()
    view = self.create_view(DetailsMyServiceView)
    assert view.is_displayed
    # TODO - remove sleep when BZ 1496233 is fixed
    time.sleep(10)
    assert view.notification.assert_message("Tagging successful.")


@MyService.delete.external_implementation_for(ViaSSUI)
def delete(self):
    view = navigate_to(self, 'Details')
    if self.appliance.version >= "5.8":
        view.configuration.item_select('Remove')
    else:
        view.remove_service.click()
    view = self.create_view(RemoveServiceView)
    view.remove.click()
    view = self.create_view(MyServicesView)
    wait_for(
        lambda: view.is_displayed, delay=15, num_sec=300,
        message="waiting for view to be displayed"
    )
    assert view.is_displayed
    # TODO - remove sleep when BZ 1496233 is fixed
    time.sleep(10)
    assert view.notification.assert_message("{} was removed.".format(self.name))


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
    return vm_obj


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


@navigator.register(MyService, 'SetOwnership')
class MyServiceSetOwnership(SSUINavigateStep):
    VIEW = SetOwnershipView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        # this is mandatory otherwise the locator is not found .
        wait_for(
            lambda: self.prerequisite_view.configuration.is_displayed, delay=5, num_sec=300,
            message="waiting for view to be displayed"
        )
        self.prerequisite_view.configuration.item_select('Set Ownership')


@navigator.register(MyService, 'EditTagsFromDetails')
class MyServiceEditTags(SSUINavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.policy_btn.item_select('Edit Tags')
