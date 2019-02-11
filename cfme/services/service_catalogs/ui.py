from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic_manageiq import Accordion, ManageIQTree
from widgetastic_patternfly import Button
from widgetastic.widget import Text, View

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.services.requests import RequestsView
from cfme.services.service_catalogs import ServiceCatalogs, BaseOrderForm
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to, ViaUI


class ServicesCatalogsView(BaseLoggedInPage):
    title = Text("#explorer_title_text")

    @property
    def in_service_catalogs(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Services', 'Catalogs'])

    @View.nested
    class service_catalogs(Accordion):  # noqa
        ACCORDION_NAME = "Service Catalogs"

        tree = ManageIQTree()

    @property
    def is_displayed(self):
        return (
            self.in_service_catalogs and
            self.title.text == 'All Services' and
            self.service_catalogs.is_opened and
            self.service_catalogs.tree.currently_selected == ["All Services"])


class OrderForm(ServicesCatalogsView, BaseOrderForm):
    pass


class ServiceCatalogsDefaultView(ServicesCatalogsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_service_catalogs and
            self.title.text == 'All Services' and
            self.service_catalogs.is_opened)


class DetailsServiceCatalogView(ServicesCatalogsView):
    title = Text("#explorer_title_text")

    order_button = Button("Order")

    @property
    def is_displayed(self):
        return (
            self.in_service_catalogs and self.service_catalogs.is_opened and
            self.title.text == 'Service "{}"'.format(self.context['object'].name)
        )


class OrderServiceCatalogView(OrderForm):
    title = Text('#explorer_title_text')
    submit_button = Button('Submit')

    @property
    def is_displayed(self):
        return (
            self.in_service_catalogs and
            self.service_catalogs.is_opened and
            'Service "{}"'.format(self.context['object'].name) in self.title.text and
            self.submit_button.is_displayed
        )


@MiqImplementationContext.external_for(ServiceCatalogs.order, ViaUI)
def order(self):
    view = navigate_to(self, 'Order')
    if self.stack_data:
        view.fill(self.stack_data)
    if self.dialog_values:
        view.fill(self.dialog_values)
    if self.ansible_dialog_values:
        view.fill(self.ansible_dialog_values)
    view.submit_button.wait_displayed()
    view.submit_button.click()
    view = self.create_view(RequestsView, wait='10s')
    view.flash.assert_no_error()
    view.flash.assert_success_message("Order Request was Submitted")
    return self.appliance.collections.requests.instantiate(self.name, partial_check=True)


@navigator.register(Server)
class ServiceCatalogsDefault(CFMENavigateStep):
    VIEW = ServiceCatalogsDefaultView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'Catalogs')


@navigator.register(ServiceCatalogs, 'All')
class ServiceCatalogsAll(CFMENavigateStep):
    VIEW = ServicesCatalogsView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'Catalogs')
        self.view.service_catalogs.tree.click_path("All Services")


@navigator.register(ServiceCatalogs, 'Details')
class ServiceCatalogDetails(CFMENavigateStep):
    VIEW = DetailsServiceCatalogView

    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.service_catalogs.tree.click_path(
            "All Services",
            self.obj.catalog.name,
            self.obj.name
        )


@navigator.register(ServiceCatalogs, 'Order')
class ServiceCatalogOrder(CFMENavigateStep):
    VIEW = OrderServiceCatalogView

    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.order_button.click()
