import time

from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import Text
from widgetastic_patternfly import Button

from cfme.base.ssui import SSUIBaseLoggedInPage
from cfme.services.service_catalogs import BaseOrderForm
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ssui import navigate_to
from cfme.utils.appliance.implementations.ssui import navigator
from cfme.utils.appliance.implementations.ssui import SSUINavigateStep
from cfme.utils.appliance.implementations.ssui import ViaSSUI
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Notification
from widgetastic_manageiq import SSUIServiceCatalogcard


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


class OrderForm(ServiceCatalogsView, BaseOrderForm):
    pass


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
    alert = Text('.//div[contains(@class, "alert")]')

    @property
    def is_displayed(self):
        return self.title.text == "Shopping Cart"


@MiqImplementationContext.external_for(ServiceCatalogs.add_to_shopping_cart, ViaSSUI)
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


@MiqImplementationContext.external_for(ServiceCatalogs.order, ViaSSUI)
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
    return self.appliance.collections.requests.instantiate(self.name, partial_check=True)


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

    def step(self, *args, **kwargs):
        self.prerequisite_view.shopping_cart.click()
