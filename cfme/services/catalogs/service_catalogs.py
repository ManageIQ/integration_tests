from widgetastic.widget import Text
from widgetastic_patternfly import Button, Input, BootstrapSelect
from widgetastic.exceptions import NoSuchElementException
from navmazing import NavigateToAttribute, NavigateToSibling
from utils.update import Updateable
from utils.pretty import Pretty
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.base import Server

from . import ServicesCatalogView


class OrderForm(ServicesCatalogView):
    title = Text('#explorer_title_text')

    timeout = Input(name='stack_timeout')
    db_user = Input(name="param_DBUser__protected")
    db_root_password = Input(name='param_DBRootPassword__protected')
    select_instance_type = BootstrapSelect("param_InstanceType")
    stack_name = Input(name='stack_name')
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


class ServiceCatalogs(Updateable, Pretty, Navigatable):

    def __init__(self, catalog=None, name=None, stack_data=None,
                 dialog_values=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.catalog = catalog
        self.name = name
        self.stack_data = stack_data
        self.dialog_values = dialog_values

    def order(self):
        view = navigate_to(self, 'Order')
        if self.stack_data:
            view.fill(self.stack_data)
        if self.dialog_values:
            view.fill(self.dialog_values)
        view.submit_button.click()
        # Request page is displayed after this hence not asserting for view
        view.flash.assert_success_message("Order Request was Submitted")


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
                    self.obj.catalog, self.obj.name)
        except:
            raise NoSuchElementException()


@navigator.register(ServiceCatalogs, 'Order')
class ServiceCatalogOrder(CFMENavigateStep):
    VIEW = OrderServiceCatalogView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.order_button.click()
