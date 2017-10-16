import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.exceptions import NoSuchElementException

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.networks.views import (NetworkRouterDetailsView, NetworkRouterView, NetworkRouterAddView,
                                 NetworkRouterEditView)
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

    def delete(self):
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Delete this Router', handle_alert=True)
        view.flash.assert_success_message('Delete initiated for 1 Network Router.')

    def edit(self, name=None, change_external_gw=False, ext_network=None, ext_network_subnet=None):
        view = navigate_to(self, 'Edit')
        if name:
            view.router_name.fill(name)
        if change_external_gw:
            view.ext_gateway.click()
            if not self.ext_network:
                view.network_name.fill(ext_network)
                view.subnet_name.fill(ext_network_subnet)
        view.save.click()
        view.flash.assert_success_message('Network Router "{}" updated'.format(name))
        self.name = name
        if change_external_gw and not self.ext_network:
            self.ext_network = ext_network
        elif change_external_gw and self.ext_network:
            self.ext_network = None

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
        """ Return network that router connected to"""
        view = navigate_to(self, 'Details')
        return view.entities.relationships.get_text_of('Cloud Network')

    @property
    def cloud_tenant(self):
        """ Return tenant that router belongs to"""
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
        view = navigate_to(self, 'Add')
        view.network_manager.fill(network_manager)
        view.router_name.fill(name)
        if has_external_gw:
            view.ext_gateway.click()
            view.network_name.fill(ext_network)
            view.subnet_name.fill(ext_network_subnet)
        view.cloud_tenant.fill(tenant)
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
