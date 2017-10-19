import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.exceptions import NoSuchElementException

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.networks.views import (NetworkRouterDetailsView, NetworkRouterView, NetworkRouterAddView,
                                 NetworkRouterEditView, NetworkRouterAddInterfaceView)
from cfme.utils import version
from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.wait import wait_for


@attr.s
class NetworkRouter(WidgetasticTaggable, BaseEntity):
    """ Class representing network ports in sdn"""
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'NetworkRouter'
    string_name = 'NetworkRouter'
    quad_name = None
    db_types = ['NetworkRouter']

    name = attr.ib()
    provider_obj = attr.ib()
    ext_network = attr.ib()

    def add_interface(self, subnet_name):
        """Adds subnet as an interface to current router

        Args:
            subnet_name: (str) name of the subnet to be added
        """
        view = navigate_to(self, 'AddInterface')
        view.subnet_name.fill(subnet_name)
        view.add.click()
        success_msg = 'Subnet "{subnet}" added to Router "{router}"'.format(subnet=subnet_name,
                                                                            router=self.name)
        view.flash.assert_success_message(success_msg)

    def delete(self):
        """Deletes current cloud router"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Delete this Router', handle_alert=True)
        view.flash.assert_success_message('Delete initiated for 1 Network Router.')

    def edit(self, name=None, change_external_gw=None, ext_network=None, ext_network_subnet=None):
        """Edit this router

        Args:
            name: (str) new name of router
            change_external_gw: (bool) external gateway, True stands for 'Yes', False - 'No'
            ext_network: (str) name of external network to be connected as gateway to router.
                applicable if 'external gateway' is enabled
            ext_network_subnet: (str) name of subnet of ext_network.
                applicable if 'external gateway' is enabled
        """
        view = navigate_to(self, 'Edit')
        view.fill({'router_name': name,
                   'ext_gateway': change_external_gw,
                   'network_name': ext_network,
                   'subnet_name': ext_network_subnet})
        view.save.click()
        success_msg = 'Network Router "{}" updated'.format(name if name else self.name)
        view.flash.assert_success_message(success_msg)
        if name:
            self.name = name
        if change_external_gw is False:
            self.ext_network = None
        if ext_network:
            self.ext_network = ext_network

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
        except (ItemNotFound, NoSuchElementException):
            return False
        else:
            return True

    @property
    def cloud_network(self):
        """ Return name of network that router connected to"""
        view = navigate_to(self, 'Details')
        return view.entities.relationships.get_text_of('Cloud Network')

    @property
    def cloud_tenant(self):
        """ Return name of tenant that router belongs to"""
        view = navigate_to(self, 'Details')
        return view.entities.relationships.get_text_of('Cloud Tenant')

    @property
    def provider(self):
        from cfme.networks.provider import NetworkProvider
        return parent_of_type(self, NetworkProvider)

    @property
    def network_provider(self):
        """ Returns network provider """
        if self.provider:
            return self.provider
        # otherwise get provider name from ui
        view = navigate_to(self, 'Details')
        try:
            prov_name = view.entities.relationships.get_text_of("Network Manager")
            collection = self.appliance.collections.network_provider
            return collection.instantiate(name=prov_name)
        except ItemNotFound:  # BZ 1480577
            return None


@attr.s
class NetworkRouterCollection(BaseCollection):
    """ Collection object for NetworkRouter object
        Note: Network providers object are not implemented in mgmt
    """

    ENTITY = NetworkRouter

    def create(self, name, provider, tenant, network_manager, has_external_gw=False,
               ext_network=None, ext_network_subnet=None):
        """Create network router

        Args:
            name: (str) name of router
            provider: crud object of OpenStack cloud provider
            tenant: (str) name of tenant to place router to
            network_manager: (str) name of network manager
            has_external_gw: (bool) represents if router has external gateway
            ext_network: (str) name of the external cloud network
                to be connected as a gateway to the router.
                Is used if has_external_gw == 'Yes'
            ext_network_subnet: (str) name of the subnet of ext_network.
                Is used if has_external_gw == 'Yes'
        Returns: instance of cfme.networks.network_router.NetworkRouter
        """
        view = navigate_to(self, 'Add')
        form_params = {'network_manager': network_manager,
                       'router_name': name,
                       'cloud_tenant': tenant}
        if has_external_gw:
            form_params.update({'ext_gateway': has_external_gw,
                                'network_name': ext_network,
                                'subnet_name': ext_network_subnet})
        view.fill(form_params)
        view.add.click()
        view.flash.assert_success_message('Network Router "{}" created'.format(name))
        router = self.instantiate(name, provider, ext_network)
        # Refresh provider's relationships to have new router displayed
        wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
        wait_for(lambda: router.exists, timeout=100, fail_func=router.browser.refresh)
        return router

    def all(self):
        if self.filters.get('parent'):
            view = navigate_to(self.filters.get('parent'), 'NetworkRouters')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=r.name) for r in list_networks_obj]


@navigator.register(NetworkRouterCollection, 'All')
class All(CFMENavigateStep):
    VIEW = NetworkRouterView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Network Routers')


@navigator.register(NetworkRouter, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = NetworkRouterDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()


@navigator.register(NetworkRouterCollection, 'Add')
class AddRouter(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = NetworkRouterAddView

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Router')


@navigator.register(NetworkRouter, 'Edit')
class EditRouter(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = NetworkRouterEditView

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Router')


@navigator.register(NetworkRouter, 'AddInterface')
class AddInterface(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = NetworkRouterAddInterfaceView

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add Interface to this Router')
