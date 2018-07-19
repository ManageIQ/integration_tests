from navmazing import NavigateToAttribute, NavigateToSibling

from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import Select, Text, View
from widgetastic_patternfly import Button

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.services.requests import RequestsView
from cfme.services.service_catalogs import ServiceCatalogs, BaseOrderForm
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to, ViaUI
from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Accordion, ManageIQTree


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
            self.in_explorer and
            self.title.text == 'All Services' and
            self.service_catalogs.is_opened)


class DetailsServiceCatalogView(ServicesCatalogsView):
    title = Text("#explorer_title_text")

    order_button = Button("Order")

    @property
    def is_displayed(self):
        return (
            self.in_explorer and self.service_catalogs.is_opened and
            self.title.text == 'Service "{}"'.format(self.context['object'].name)
        )


class OrderServiceCatalogView(OrderForm):
    title = Text('#explorer_title_text')
    submit_button = Button('Submit')

    @property
    def is_displayed(self):
        return (
            self.in_service_catalogs and self.service_catalogs.is_opened and
            'Service "{}"'.format(self.context['object'].name) in self.title.text
        )


@MiqImplementationContext.external_for(ServiceCatalogs.order, ViaUI)
def order(self):
    view = navigate_to(self, 'Order', wait_for_view=True)
    if self.stack_data:
        view.fill(self.stack_data)
    if self.dialog_values:
        view.fill(self.dialog_values)
    if self.ansible_dialog_values:
        view.fill(self.ansible_dialog_values)
    msg = "Order Request was Submitted"
    if self.appliance.version < "5.9":
        msg_type = "success"
    else:
        msg_type = "info"
    # Additional check if submit is done, to cover case when last filled field value is not taken
    # Can appear every 2nd case when whole module is run
    if view.is_displayed and view.submit_button.is_displayed:
        view.submit_button.click()
    view = self.create_view(RequestsView)
    view.flash.assert_no_error()
    view.flash.assert_message(msg, msg_type)
    return self.appliance.collections.requests.instantiate(self.name, partial_check=True)


@navigator.register(Server)
class ServiceCatalogsDefault(CFMENavigateStep):
    VIEW = ServiceCatalogsDefaultView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Services', 'Catalogs')


@navigator.register(ServiceCatalogs, 'All')
class ServiceCatalogsAll(CFMENavigateStep):
    VIEW = ServicesCatalogsView

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
