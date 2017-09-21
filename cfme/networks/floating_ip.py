<<<<<<< HEAD
import attr

=======
>>>>>>> Adding Floating IP
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.exceptions import NoSuchElementException

from cfme.common import WidgetasticTaggable
<<<<<<< HEAD
from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.networks.views import (FloatingIPView, FloatingIPDetailsView,
                                 FloatingIPAddView)
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for


@attr.s
class FloatingIP(WidgetasticTaggable, BaseEntity):
=======
from cfme.networks.add_object_views import AddNewFloatingIPView
from cfme.networks.views import FloatingIPView, FloatingIPDetailsView
from cfme.utils import version
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class FloatingIPCollection(Navigatable):
    ''' Collection object for Floating ip object '''

    def __init__(self, appliance, parent_provider=None):
        Navigatable.__init__(self, appliance=appliance)
        self.parent = parent_provider

    def instantiate(self, address):
        return FloatingIP(address=address, appliance=self.appliance, collection=self)

    def all(self):
        if self.parent:
            view = navigate_to(self.parent, 'FloatingIPs')
        else:
            view = navigate_to(self, 'All')
        try:
            list_ips_obj = [row['Address'].text for row in view.entities.elements.rows()]
        except NoSuchElementException:
            list_ips_obj = []
        return [self.instantiate(address=name) for name in list_ips_obj]


class FloatingIP(WidgetasticTaggable, Navigatable):
>>>>>>> Adding Floating IP
    ''' Class representing floating ip in sdn '''
    in_version = ('5.8', version.LATEST)
    category = "networks"
    page_name = 'floating_ip'
    string_name = 'FloatingIP'
    refresh_text = "Refresh items and relationships"
    detail_page_suffix = 'floating_ip_detail'
    quad_name = None
    db_types = ["FloatingIP"]

<<<<<<< HEAD
    address = attr.ib()
=======
    def __init__(self, address, provider=None, collection=None, appliance=None):
        self.collection = collection or FloatingIPCollection(appliance=appliance)
        Navigatable.__init__(self, appliance=self.collection.appliance)
        self.ip_address = address
        self.provider = provider
>>>>>>> Adding Floating IP

    @property
    def status(self):
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Status')

    @property
<<<<<<< HEAD
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
=======
    def address(self):
        return self.ip_address

    @property
    def exists(self):
        ips = [r.ip_address for r in self.collection.all()]
        return self.ip_address in ips
>>>>>>> Adding Floating IP


@navigator.register(FloatingIPCollection, 'All')
class All(CFMENavigateStep):
    VIEW = FloatingIPView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Floating IPs')


<<<<<<< HEAD
@navigator.register(FloatingIPCollection, 'Add')
class AddNewFloatingIP(CFMENavigateStep):
    VIEW = FloatingIPAddView
=======
@navigator.register(FloatingIPCollection, 'AddNewFloatingIP')
class AddNewFloatingIP(CFMENavigateStep):
    VIEW = AddNewFloatingIPView
>>>>>>> Adding Floating IP
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Add a new Floating IP")


@navigator.register(FloatingIP, 'Details')
class Details(CFMENavigateStep):
<<<<<<< HEAD
    prerequisite = NavigateToAttribute('parent', 'All')
=======
    prerequisite = NavigateToAttribute('collection', 'All')
>>>>>>> Adding Floating IP
    VIEW = FloatingIPDetailsView

    def step(self):
        try:
            list_ips_obj = [row for row in self.prerequisite_view.entities.elements.rows()]
        except NoSuchElementException:
            list_ips_obj = []
        for element in list_ips_obj:
            if self.obj.address == element['Address'].text:
                return element.click()
<<<<<<< HEAD
=======


@navigator.register(FloatingIP, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
>>>>>>> Adding Floating IP
