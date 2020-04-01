import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling

from cfme.common import Taggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.modeling.base import parent_of_type
from cfme.networks.views import FloatingIpAddView
from cfme.networks.views import FloatingIpDetailsView
from cfme.networks.views import FloatingIpView
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.wait import wait_for


@attr.s
class FloatingIp(Taggable, BaseEntity):
    """Class representing floating ips"""
    address = attr.ib()

    category = "networks"
    page_name = 'floating_ip'
    string_name = 'FloatingIP'
    refresh_text = "Refresh items and relationships"
    detail_page_suffix = 'floating_ip_detail'
    quad_name = None
    db_types = ["FloatingIP"]

    @property
    def status(self):
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Status')

    @property
    def provider(self):
        from cfme.networks.provider import NetworkProvider
        return parent_of_type(self, NetworkProvider)


@attr.s
class FloatingIpCollection(BaseCollection):
    """ Collection object for NetworkPort object
        Note: Network providers object are not implemented in mgmt
    """
    ENTITY = FloatingIp

    def all(self):
        floating_ips = []
        view = navigate_to(self, 'All')
        for _ in view.entities.paginator.pages():
            ips = view.entities.get_all()
            for ip in ips:
                floating_ips.append(self.instantiate(address=ip.data['address']))
        return floating_ips

    def create(self, tenant, provider, network_manager, network_name,
               floating_ip_address=None, fixed_ip_address=None, network_port_id=None):
        """Create subnet

        Args:
            tenant: (str) name of the tenant to place FIP to
            provider: crud object of Openstack cloud provider
            network_manager: (str) name of network manager
            network_name: (str) name of the network to create FIP under
            floating_ip_address: (str) Floating Address(Name) of FIP, for example: 192.168.12.2/24
            fixed_ip_address: (str) Fixed Address(Name) of FIP, for example: 192.168.12.2/24
            network_port_id: (str) Id of network port to associate FIP with

        Returns: instance of cfme.networks.floating_ips.FloatingIp
        """
        view = navigate_to(self, 'Add')
        view.fill({'network_manager': network_manager,
                   'network': network_name,
                   'network_port_id': network_port_id,
                   'floating_ip_address': floating_ip_address,
                   'fixed_ip_address': fixed_ip_address,
                   'cloud_tenant': tenant})
        view.add.click()
        view.flash.assert_success_message(f'Floating IP "{floating_ip_address}" created')
        floating_ip = self.instantiate(floating_ip_address, provider, network_name)
        # Refresh provider's relationships to have new FIP displayed
        wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
        wait_for(lambda: floating_ip.exists, timeout=100, fail_func=floating_ip.browser.refresh)
        return floating_ip


@navigator.register(FloatingIpCollection, 'All')
class All(CFMENavigateStep):
    VIEW = FloatingIpView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Networks', 'Floating IPs')

    def resetter(self, *args, **kwargs):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(FloatingIp, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = FloatingIpDetailsView

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.entities.get_entity(address=self.obj.address,
                                                       surf_pages=True).click()
        except Exception:
            raise ItemNotFound('Floating IP not found on the page')


@navigator.register(FloatingIpCollection, 'Add')
class AddFloatingIP(CFMENavigateStep):
    VIEW = FloatingIpAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Floating IP')
