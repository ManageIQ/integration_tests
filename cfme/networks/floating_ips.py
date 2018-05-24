import attr
from navmazing import NavigateToAttribute

from cfme.common import Taggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.networks.views import FloatingIpDetailsView, FloatingIpView
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


@attr.s
class FloatingIp(Taggable, BaseEntity):
    """Class representing floating ips"""
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
class FloatingIpCollection(BaseCollection):
    """ Collection object for NetworkPort object
        Note: Network providers object are not implemented in mgmt
    """

    ENTITY = FloatingIp

    def all(self):
        view = navigate_to(self, 'All')
        all_ips = view.entities.get_all(surf_pages=True)
        list_floating_ip_obj = []
        for ip in all_ips:
            # as for 5.9 floating ip doesn't have name att, will get name as address from data
            list_floating_ip_obj.append(ip.name if ip.name else ip.data['address'])
        return [self.instantiate(address=name) for name in list_floating_ip_obj]


@navigator.register(FloatingIpCollection, 'All')
class All(CFMENavigateStep):
    VIEW = FloatingIpView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Floating IPs')

    def resetter(self):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(FloatingIp, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = FloatingIpDetailsView

    def step(self):
        # as for 5.9 floating ip doesn't have name att, will get id for navigation
        # for 5.8 floating ip table view doesn't have name to search for,
        # in this case we will use address
        if self.obj.appliance.version < '5.9':
            try:
                element = self.prerequisite_view.entities.get_entity(
                    name=self.obj.address, surf_pages=True)
            except ItemNotFound:
                element = self.prerequisite_view.entities.get_entity(
                    address=self.obj.address, surf_pages=True)
        else:
            all_items = self.prerequisite_view.entities.get_all(surf_pages=True)
            for entity in all_items:
                if entity.data['address'] == self.obj.address:
                    entity_id = entity.data['id']
                    element = self.prerequisite_view.entities.get_entity(
                        entity_id=entity_id, surf_pages=True)
                    break
        try:
            element.click()
        except Exception:
            raise ItemNotFound('Floating IP not found on the page')
