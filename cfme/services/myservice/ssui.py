from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import Select
from widgetastic.widget import Text
from widgetastic.widget import TextInput
from widgetastic_patternfly import Button
from widgetastic_patternfly import CandidateNotFound
from widgetastic_patternfly import Input
from widgetastic_patternfly import Kebab

from cfme.base.ssui import SSUIBaseLoggedInPage
from cfme.exceptions import ItemNotFound
from cfme.services.myservice import MyService
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ssui import navigate_to
from cfme.utils.appliance.implementations.ssui import navigator
from cfme.utils.appliance.implementations.ssui import SSUINavigateStep
from cfme.utils.appliance.implementations.ssui import ViaSSUI
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Notification
from widgetastic_manageiq import SSUIAppendToBodyDropdown
from widgetastic_manageiq import SSUICardPFInfoStatus
from widgetastic_manageiq import SSUIDropdown
from widgetastic_manageiq import SSUIlist
from widgetastic_manageiq import SSUIPaginationPane
from widgetastic_manageiq import TimelinesChart


class MyServicesView(SSUIBaseLoggedInPage):
    title = Text(locator='//li[@class="active"]')
    service = SSUIlist()
    notification = Notification()
    paginator = SSUIPaginationPane()

    @property
    def in_myservices(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["", "My Services"])

    @property
    def is_displayed(self):
        return self.in_myservices and self.title.text == "My Services"


class PowerIcon(Text):
    @property
    def power_status(self):
        return self.browser.get_attribute('uib-tooltip', self).split(': ')[1]


class DetailsMyServiceView(MyServicesView):
    title = Text(locator='//li[@class="active"]')

    @property
    def is_displayed(self):
        return (self.in_myservices and
                self.title.text in {self.context['object'].name, 'Service Details'})

    notification = Notification()
    policy = SSUIDropdown('Policy')
    power_operations = Kebab(
        locator='.//div[contains(@class, "dropdown-kebab-pf") and ./button][1]')
    access_dropdown = SSUIAppendToBodyDropdown('Access')
    remove_service = Button("Remove Service")
    configuration = SSUIDropdown('Configuration')
    lifecycle = SSUIDropdown('Lifecycle')
    console_button = Button(tooltip="HTML5 console", classes=['open-console-button'])
    retirement_state = TextInput(
        locator=".//label[text()='Retirement State']/parent::div/div/input"
    )
    resource_power_status = PowerIcon(".//span/i[contains(@class, 'pficon') and contains("
                                      "@uib-tooltip,'Power State')]")
    standard_output = Text('.//div[@class="well"]')


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
    title = Text(locator='//h4[@id="myModalLabel"]')

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.name.is_displayed and
            self.title.text == "Edit Service"
        )


class SetOwnershipView(SetOwnershipForm):
    title = Text(locator='//*[@id="myModalLabel"]')

    save_button = Button('Save')

    @property
    def is_displayed(self):
        return (
            self.select_owner.is_displayed and
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
            self.title.text == 'Edit Tags' and
            self.tag_category.is_displayed and
            self.tag_name.is_displayed)


class RemoveServiceView(MyServicesView):
    title = Text(locator='//h4[@id="myModalLabel"]')

    remove = Button('Yes, Remove Service')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.remove.is_displayed and
            self.title.text == 'Remove Service')


class RetireServiceView(MyServicesView):
    title = Text(locator='//h4[@class="modal-title"]')

    retire = Button('OK')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.retire.is_displayed and
            self.title.text == "Retire Services"
        )


class MyServiceVMDetailsView(MyServicesView):
    # TODO: This view needs enhancement by FA owner.
    #  TimelinesChart Widget not supporting completely need improvements as per SSUI.

    # I won't found better way than indexing on this Page.
    vm_info = SSUICardPFInfoStatus(locator="(.//div[contains(@class, 'card-pf-info-status')])[1]")
    provider_info = SSUICardPFInfoStatus(
        locator="(.//div[contains(@class, 'card-pf-info-status')])[2]"
    )
    snapshots = SSUIDropdown("Snapshots")
    power_operations = SSUIDropdown("Power Operations")
    timeline = TimelinesChart(locator='.//*[@class="timeline"]')

    @property
    def is_displayed(self):
        return (
            self.in_myservices
            and self.timeline.is_displayed
            and self.power_operations.is_displayed
        )


@MiqImplementationContext.external_for(MyService.update, ViaSSUI)
def update(self, updates):
    view = navigate_to(self, 'Edit')
    view.fill_with(updates, on_change=view.save_button, no_change=view.cancel_button)
    view.flash.assert_no_error()
    view = self.create_view(DetailsMyServiceView, override=updates)
    message_present, _ = wait_for(view.notification.assert_message,
                                  func_args=[f'{self.name} was edited.'],
                                  timeout=10)
    assert message_present


@MiqImplementationContext.external_for(MyService.set_ownership, ViaSSUI)
def set_ownership(self, owner, group):
    view = navigate_to(self, 'SetOwnership')
    view.fill({'select_owner': owner,
               'select_group': group})
    view.save_button.click()
    view = self.create_view(DetailsMyServiceView)
    assert view.is_displayed
    message_present, _ = wait_for(view.notification.assert_message,
                                  func_args=['Setting ownership.'],
                                  timeout=10)
    assert message_present
    view.browser.refresh()  # WA until ManageIQ/integration_tests:7157 is solved


@MiqImplementationContext.external_for(MyService.edit_tags, ViaSSUI)
def edit_tags(self, tag, value):
    view = navigate_to(self, 'EditTagsFromDetails')
    view.fill({'tag_category': tag,
               'tag_name': value})
    view.add_tag.click()
    view.save.click()
    view = self.create_view(DetailsMyServiceView)
    assert view.is_displayed
    message_present, _ = wait_for(view.notification.assert_message,
                                  func_args=["Tagging successful."],
                                  timeout=10)
    assert message_present


@MiqImplementationContext.external_for(MyService.delete, ViaSSUI)
def delete(self):
    view = navigate_to(self, 'Details')
    if self.appliance.version >= "5.8":
        view.configuration.item_select('Remove')
    else:
        view.remove_service.click()
    view = self.create_view(RemoveServiceView)
    view.remove.click()
    view = self.create_view(MyServicesView, wait=300)
    message_present, _ = wait_for(view.notification.assert_message,
                                  func_args=[f"{self.name} was removed."],
                                  timeout=10)
    assert message_present


@MiqImplementationContext.external_for(MyService.launch_vm_console, ViaSSUI)
def launch_vm_console(self, catalog_item):
    navigate_to(self, 'VM Console')
    # TODO need to remove 0001 from the line below and find correct place/way to put it in code
    collection = catalog_item.provider.appliance.provider_based_collection(catalog_item.provider)
    vm_obj = collection.instantiate(
        '{}{}'.format(catalog_item.prov_data['catalog']['vm_name'], '0001'),
        catalog_item.provider,
        template_name=catalog_item.name
    )
    wait_for(
        func=lambda: vm_obj.vm_console, num_sec=30, delay=2, handle_exception=True,
        message="waiting for VM Console window to open"
    )
    return vm_obj


@MiqImplementationContext.external_for(MyService.exists.getter, ViaSSUI)
def exists(self):
    try:
        navigate_to(self, 'Details')
        return True
    except (CandidateNotFound, ItemNotFound):
        return False


@MiqImplementationContext.external_for(MyService.is_retired.getter, ViaSSUI)
def is_retired(self):
    view = navigate_to(self, 'Details')
    return view.retirement_state.value == "retired"


@MiqImplementationContext.external_for(MyService.retire, ViaSSUI)
def retire(self):
    view = navigate_to(self, 'Retire')
    view.retire.click()
    if self.appliance.version < "5.10":
        view = self.create_view(MyServicesView, wait='20s')
        assert view.notification.assert_message(f"{self.name} was retired.")
    else:
        view = self.create_view(DetailsMyServiceView, wait='20s')
        assert view.notification.assert_message("Service Retire - Request Created")
    return self.appliance.collections.requests.instantiate(self.name, partial_check=True)


@MiqImplementationContext.external_for(MyService.service_power, ViaSSUI)
def service_power(self, power=None):
    view = navigate_to(self, 'Details')
    view.power_operations.item_select(power)
    view.wait_displayed('60s')
    # TODO - assert vm state through rest api


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
        wait_for(
            lambda: self.prerequisite_view.service.is_displayed(self.obj.name),
            delay=5, num_sec=300,
            fail_func=self.prerequisite_view.browser.refresh,
            message="waiting for view to be displayed"
        )
        self.prerequisite_view.service.click_at(self.obj.name)


@navigator.register(MyService, 'Edit')
class MyServiceEdit(SSUINavigateStep):
    VIEW = EditMyServiceView

    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Edit')


@navigator.register(MyService, 'VM Console')
class LaunchVMConsole(SSUINavigateStep):
    VIEW = DetailsMyServiceView

    def prerequisite(self):
        return navigate_to(self.obj, 'Details')

    def step(self, *args, **kwargs):
        if self.appliance.version < "5.11":
            self.prerequisite_view.access_dropdown.item_select('VM Console')
        else:
            self.prerequisite_view.access_dropdown.item_select('VM HTML5 Console')


@navigator.register(MyService, 'SetOwnership')
class MyServiceSetOwnership(SSUINavigateStep):
    VIEW = SetOwnershipView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
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

    def step(self, *args, **kwargs):
        self.prerequisite_view.policy.item_select('Edit Tags')


@navigator.register(MyService, 'Retire')
class MyServiceRetire(SSUINavigateStep):
    VIEW = RetireServiceView

    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.lifecycle.item_select('Retire')


@navigator.register(MyService, "VMDetails")
class MyServiceVMDetails(SSUINavigateStep):
    VIEW = MyServiceVMDetailsView

    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.service.click_at(self.obj.vm_name)
