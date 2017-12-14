from navmazing import NavigateToAttribute, NavigateToSibling

from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import VersionPick
from widgetastic.widget import Text, View, Select
from widgetastic_patternfly import Button, Input, BootstrapSelect

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.services.requests import RequestsView
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to, ViaUI
from cfme.utils.blockers import BZ
from cfme.utils.version import Version
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Accordion, ManageIQTree


class ServicesCatalogView(BaseLoggedInPage):
    @property
    def in_service_catalogs(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Services', 'Catalogs'])

    @property
    def is_displayed(self):
        return (
            self.in_service_catalogs and
            self.configuration.is_displayed and
            not self.catalogs.is_dimmed)

    @View.nested
    class service_catalogs(Accordion):  # noqa
        ACCORDION_NAME = "Service Catalogs"

        tree = ManageIQTree()


class OrderForm(ServicesCatalogView):
    title = Text('#explorer_title_text')
    dialog_title = Text(
        VersionPick({
            Version.lowest(): ".//div[@id='main_div']//h3",
            "5.9": ".//div[@id='main_div']//h2"
        })
    )

    timeout = Input(name='stack_timeout')
    db_user = Input(name="param_DBUser__protected")
    db_root_password = Input(name='param_DBRootPassword__protected')
    resource_group = BootstrapSelect("resource_group")
    mode = BootstrapSelect('deploy_mode')
    select_instance_type = BootstrapSelect("param_InstanceType")
    vm_user = Input(name='param_adminUserName')
    vm_password = Input(name="param_adminPassword__protected")
    vm_size = BootstrapSelect('param_virtualMachineSize')
    user_image = BootstrapSelect("param_userImageName")
    os_type = BootstrapSelect('param_operatingSystemType')
    stack_name = VersionPick({
        '5.9': Input(
            locator='.//input[../../../div[normalize-space(.)="Stack Name"]]'),
        Version.lowest(): Input(name='stack_name')})
    stack_timeout = VersionPick({
        '5.9': Input(
            locator='.//input[../../../div[contains(normalize-space(.), "Timeout")]]'),
        Version.lowest(): Input(name='stack_timeout')})

    vm_name = VersionPick({
        '5.9': Input(
            locator='.//input[../../../div[contains(normalize-space(.), "Virtual Machine Name")]]'),
        Version.lowest(): Input(name="param_virtualMachineName")})

    key_name = VersionPick({
        '5.9': Input(
            locator='.//input[../../../div[contains(normalize-space(.), "Key Name")]]'),
        Version.lowest(): Input(name="param_KeyName")})
    role_arn = Input(locator='.//input[../../../div[contains(normalize-space(.), "Role ARN")]]')
    ssh_location = Input(name="param_SSHLocation")

    flavor = Input(name='param_flavor')
    image = Input(name="param_image")
    key = Input(name='param_key')
    private_network = Input(name="param_private_network")
    default_select_value = VersionPick({
        '5.9': Select(locator='.//select[../../'
                              'div[contains(normalize-space(.), "Service Level")]]'),
        Version.lowest(): BootstrapSelect('service_level')})

    machine_credential = BootstrapSelect("credential")
    hosts = Input(name="hosts")


class ServiceCatalogsView(ServicesCatalogView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'All Services' and
            self.service_catalogs.is_opened and
            self.service_catalogs.tree.currently_selected == ["All Services"])


class ServiceCatalogsDefaultView(ServicesCatalogView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'All Services' and
            self.service_catalogs.is_opened)


class DetailsServiceCatalogView(ServicesCatalogView):
    title = Text("#explorer_title_text")

    order_button = Button("Order")

    @property
    def is_displayed(self):
        return (
            self.in_explorer and self.service_catalogs.is_opened and
            self.title.text == 'Service "{}"'.format(self.context['object'].name)
        )


class OrderServiceCatalogView(OrderForm):
    submit_button = Button('Submit')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and self.service_catalogs.is_opened and
            self.title.text == 'Order Service "{}"'.format(self.context['object'].name)
        )


@MiqImplementationContext.external_for(ServiceCatalogs.order, ViaUI)
def order(self):
    view = navigate_to(self, 'Order')
    wait_for(lambda: view.dialog_title.is_displayed, timeout=10)
    if self.stack_data:
        view.fill(self.stack_data)
    if self.dialog_values:
        view.fill(self.dialog_values)
    if self.ansible_dialog_values:
        view.fill(self.ansible_dialog_values)
    if self.stack_data and self.appliance.version > '5.9':
        view.fill({'role_arn': "default"})
    msg = "Order Request was Submitted"
    if self.appliance.version < "5.9":
        msg_type = "success"
    else:
        msg_type = "info"
    # TODO Remove once repaired
    if BZ(1513541, forced_streams=['5.9']).blocks:
        raise NotImplementedError("Service Order is broken - check BZ 1513541")
    if self.stack_data and self.appliance.version > '5.9':
        view.fill({'role_arn': "default"})
    view.submit_button.click()
    view = self.create_view(RequestsView)
    view.flash.assert_no_error()
    view.flash.assert_message(msg, msg_type)


@navigator.register(Server)
class ServiceCatalogsDefault(CFMENavigateStep):
    VIEW = ServiceCatalogsDefaultView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Services', 'Catalogs')


@navigator.register(ServiceCatalogs, 'All')
class ServiceCatalogsAll(CFMENavigateStep):
    VIEW = ServiceCatalogsView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Services', 'Catalogs')
        self.view.service_catalogs.tree.click_path("All Services")


@navigator.register(ServiceCatalogs, 'Details')
class ServiceCatalogDetails(CFMENavigateStep):
    VIEW = DetailsServiceCatalogView

    prerequisite = NavigateToSibling('All')

    def step(self):
        try:
            self.prerequisite_view.service_catalogs.tree.click_path("All Services",
                 self.obj.catalog.name, self.obj.name)
        except:
            raise NoSuchElementException()


@navigator.register(ServiceCatalogs, 'Order')
class ServiceCatalogOrder(CFMENavigateStep):
    VIEW = OrderServiceCatalogView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.order_button.click()
