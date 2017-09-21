from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text
from widgetastic_manageiq import SSUIlist, SSUIDropdown
from widgetastic_patternfly import Input, Button

from cfme.base.ssui import SSUIBaseLoggedInPage
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ssui import (
    navigator,
    SSUINavigateStep,
    navigate_to,
    ViaSSUI
)

class ServiceCatalogsView(SSUIBaseLoggedInPage):
    title = Text(locator='//li[@class="active"]')

    @property
    def in_service_catalogs(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["", "Service Catalog"])

    @property
    def is_displayed(self):
        return self.in_service_catalogs and self.title.text == "Service Catalog"


class DetailsServiceCatalogsView(ServiceCatalogsView):
    title = Text(locator='//li[@class="active"]')

    @property
    def is_displayed(self):
        return (self.in_service_catalogs and
               self.title.text in {self.context['object'].name})

    add_to_shopping_cart = Button('Add to Shopping Cart')


@ServiceCatalogs.add_to_shopping_cart.external_implementation_for(ViaSSUI)
def add_to_shopping_cart(self):
    view = navigate_to(self, 'Details')
    view.add_to_shopping_cart.click()
    view.flash.assert_no_error()
    # TODO - implement notifications and then assert.


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
