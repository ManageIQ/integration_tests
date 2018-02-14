from navmazing import NavigateToAttribute, NavigateToSibling

from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import (deflatten_dict, Parameter, ParametrizedLocator, ParametrizedString,
    VersionPick)
from widgetastic.widget import ParametrizedView, Select, Text, View
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
from widgetastic_manageiq import Accordion, ManageIQTree, DialogFieldDropDownList


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
    """Represents the order form of a service.
    This form doesn't have a static set of elements apart from titles and buttons. In the most cases
    the fields can be either regular inputs or dropdowns. Their locators depend on field names. In
    order to find and fill required fields a parametrized view is used here. The keys of a fill
    dictionary should match ids of the fields. For instance there is a field with such html
    <input id="some_key"></input>, so a fill dictionary should look like that:
    {"some_key": "some_value"}
    """
    title = Text('#explorer_title_text')
    dialog_title = Text(
        VersionPick({
            Version.lowest(): ".//div[@id='main_div']//h3",
            "5.9": ".//div[@id='main_div']//h2"
        })
    )

    @ParametrizedView.nested
    class fields(ParametrizedView):  # noqa
        PARAMETERS = ("key",)
        input = Input(id=Parameter("key"))
        select = Select(id=Parameter("key"))
        param_input = Input(id=ParametrizedString("param_{key}"))
        dropdown = VersionPick({
            Version.lowest(): BootstrapSelect(Parameter("key")),
            "5.9": DialogFieldDropDownList(ParametrizedLocator(".//div[@input-id={key|quote}]"))
        })
        param_dropdown = VersionPick({
            Version.lowest(): BootstrapSelect(ParametrizedString("param_{key}")),
            "5.9": DialogFieldDropDownList(
                ParametrizedLocator(".//div[@input-id='param_{key}']"))
        })

        @property
        def visible_widget(self):
            if self.input.is_displayed:
                return self.input
            elif self.dropdown.is_displayed:
                return self.dropdown
            elif self.param_input.is_displayed:
                return self.param_input
            elif self.param_dropdown.is_displayed:
                return self.param_dropdown
            elif self.select.is_displayed:
                return self.select

        def read(self):
            return self.visible_widget.read()

        def fill(self, value):
            return self.visible_widget.fill(value)

    def fill(self, fill_data):
        values = deflatten_dict(fill_data)
        was_change = False
        self.before_fill(values)
        for key, value in values.items():
            widget = self.fields(key)
            if value is None:
                self.logger.debug('Skipping fill of %r because value was None', key)
                continue
            try:
                if widget.fill(value):
                    was_change = True
            except NotImplementedError:
                continue

        self.after_fill(was_change)
        return was_change


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
            self.in_service_catalogs and self.service_catalogs.is_opened and
            'Service "{}"'.format(self.context['object'].name) in self.title.text
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
    msg = "Order Request was Submitted"
    if self.appliance.version < "5.9":
        msg_type = "success"
    else:
        msg_type = "info"
    # TODO Remove once repaired
    if BZ(1513541, forced_streams=['5.9']).blocks:
        raise NotImplementedError("Service Order is broken - check BZ 1513541")
    view.submit_button.click()
    if view.is_displayed and view.submit_button.is_displayed:
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
