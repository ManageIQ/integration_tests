from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text
from widgetastic_manageiq import SSUIServiceCatalogcard, SSUIInput, Notification
from widgetastic_patternfly import Input, Button, BootstrapSelect

from cfme.base.ssui import SSUIBaseLoggedInPage
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ssui import (
    navigator,
    SSUINavigateStep,
    navigate_to,
    ViaSSUI
)
from cfme.utils.wait import wait_for
import time


class ServiceCatalogsView(SSUIBaseLoggedInPage):
    title = Text(locator='//li[@class="active"]')
    service = SSUIServiceCatalogcard()

    @property
    def in_service_catalogs(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["", "Service Catalog"])

    @property
    def is_displayed(self):
        return self.in_service_catalogs and self.title.text == "Service Catalog"


class OrderForm(ServiceCatalogsView):
    title = Text('#explorer_title_text')

    service_name = SSUIInput()
    timeout = Input(name='stack_timeout')
    db_user = Input(name="param_DBUser__protected")
    db_root_password = Input(name='param_DBRootPassword__protected')
    select_instance_type = BootstrapSelect("param_InstanceType")
    stack_name = Input(name='stack_name')
    stack_timeout = Input(name='stack_timeout')
    resource_group = BootstrapSelect("resource_group")
    mode = BootstrapSelect('deploy_mode')
    vm_name = Input(name="param_virtualMachineName")
    vm_user = Input(name='param_adminUserName')
    vm_password = Input(name="param_adminPassword__protected")
    vm_size = BootstrapSelect('param_virtualMachineSize')
    user_image = BootstrapSelect("param_userImageName")
    os_type = BootstrapSelect('param_operatingSystemType')
    key_name = Input(name="param_KeyName")
    ssh_location = Input(name="param_SSHLocation")

    flavor = Input(name='param_flavor')
    image = Input(name="param_image")
    key = Input(name='param_key')
    private_network = Input(name="param_private_network")
    default_select_value = BootstrapSelect('service_level')

    machine_credential = BootstrapSelect("credential")
    hosts = Input(name="hosts")


class DetailsServiceCatalogsView(OrderForm):
    title = Text(locator='//li[@class="active"]')

    notification = Notification()
    add_to_shopping_cart = Button('Add to Shopping Cart')
    shopping_cart = Text('.//li/a[@title="Shopping cart"]')

    @property
    def is_displayed(self):
        return (
            self.in_service_catalogs and
            self.title.text == self.context['object'].name)


class ShoppingCartView(DetailsServiceCatalogsView):
    title = Text(locator='//h4[@class="modal-title"]')

    close = Button('Close')
    clear = Button('Clear')
    order = Button('Order')

    @property
    def is_displayed(self):
        return (
            self.in_service_catalogs and
            self.title.text == "Shopping Cart"
        )


@ServiceCatalogs.add_to_shopping_cart.external_implementation_for(ViaSSUI)
def add_to_shopping_cart(self):
    view = navigate_to(self, 'Details')
    wait_for(
        lambda: view.is_displayed, delay=5, num_sec=300,
        message="waiting for view to be displayed"
    )
    if self.stack_data:
        view.fill(self.stack_data)
    if self.dialog_values:
        view.fill(self.dialog_values)
    if self.ansible_dialog_values:
        view.fill(self.ansible_dialog_values)
    view.add_to_shopping_cart.click()
    view.flash.assert_no_error()
    view = self.create_view(DetailsServiceCatalogsView)
    # TODO - remove sleep when BZ 1496233 is fixed
    time.sleep(10)
    assert view.notification.assert_message("Item added to shopping cart")


@ServiceCatalogs.order.external_implementation_for(ViaSSUI)
def order(self):
    view = navigate_to(self, 'ShoppingCart')
    wait_for(
        lambda: view.is_displayed, delay=5, num_sec=300,
        message="waiting for view to be displayed"
    )
    view.order.click()
    # TODO - remove sleep when BZ 1496233 is fixed
    time.sleep(10)
    assert view.notification.assert_message("Shopping cart successfully ordered")


@navigator.register(ServiceCatalogs, 'All')
class ServiceCatalogAll(SSUINavigateStep):
    VIEW = ServiceCatalogsView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Service Catalog')


@navigator.register(ServiceCatalogs, 'Details')
class Details(SSUINavigateStep):
    VIEW = DetailsServiceCatalogsView

    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.service.click_at(self.obj.name)


@navigator.register(ServiceCatalogs, 'ShoppingCart')
class ShoppingCart(SSUINavigateStep):
    VIEW = ShoppingCartView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.shopping_cart.click()
