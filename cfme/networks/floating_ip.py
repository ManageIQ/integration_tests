import attr

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.exceptions import NoSuchElementException

from cfme.common import WidgetasticTaggable
from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.networks.views import (FloatingIPView, FloatingIPDetailsView,
                                 FloatingIPAddView)
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for


@attr.s
class FloatingIP(WidgetasticTaggable, BaseEntity):
    ''' Class representing floating ip in sdn '''
    in_version = ('5.8', version.LATEST)
    category = "networks"
    page_name = 'floating_ip'
    string_name = 'FloatingIP'
    refresh_text = "Refresh items and relationships"
    detail_page_suffix = 'floating_ip_detail'
    quad_name = None
    db_types = ["FloatingIP"]

    address = attr.ib()

    @property
    def status(self):
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Status')

    @property
    def provider(self):
        from cfme.networks.provider import NetworkProvider
        return parent_of_type(self, NetworkProvider)


@attr.s
class FloatingIPCollection(BaseCollection):
    ''' Collection object for Floating ip object '''
    ENTITY = FloatingIP

    def all(self):
        if self.filters.get('parent'):
            view = navigate_to(self.filters.get('parent'), 'FloatingIPs')
        else:
            view = navigate_to(self, 'All')
        try:
            list_ips_obj = [row['Address'].text for row in view.entities.elements.rows()]
        except NoSuchElementException:
            list_ips_obj = []
        return [self.instantiate(address=name) for name in list_ips_obj]

    def create(self, address, tenant, net_manager, provider, ext_network=None):
        view = navigate_to(self, 'Add')
        view.fill({'network_manager': net_manager})
        # dont use those in common fill method

        if current_version() < '5.9':
            view.floating_ip.fill(address)
        else:
            view.floating_ip_new.fill(address)

        view.external_network.select_by_visible_text(ext_network)
        view.cloud_tenant.select_by_visible_text(tenant)

        view.add.click()
        provider.refresh_provider_relationships()
        wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
        fip = self.instantiate(address=address)
        return fip

    def exists(self, ip):
        ips = [r.address for r in self.all()]
        return ip.address in ips


@navigator.register(FloatingIPCollection, 'All')
class All(CFMENavigateStep):
    VIEW = FloatingIPView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Floating IPs')


@navigator.register(FloatingIPCollection, 'Add')
class AddNewFloatingIP(CFMENavigateStep):
    VIEW = FloatingIPAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Add a new Floating IP")


@navigator.register(FloatingIP, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = FloatingIPDetailsView

    def step(self):
        try:
            list_ips_obj = [row for row in self.prerequisite_view.entities.elements.rows()]
        except NoSuchElementException:
            list_ips_obj = []
        for element in list_ips_obj:
            if self.obj.address == element['Address'].text:
                return element.click()
