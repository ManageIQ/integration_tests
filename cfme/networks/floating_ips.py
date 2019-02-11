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
    address = attr.ib()

    in_version = ('5.8', version.LATEST)
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
