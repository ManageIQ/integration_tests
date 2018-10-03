import attr

from cfme.common import Taggable
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.networks.views import CloudTenantDetailsView
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep

from navmazing import NavigateToAttribute


@attr.s
class CloudTenant(Taggable, BaseEntity):
    """Class representing cloud tenants"""
    in_version = ('5.10', version.LATEST)
    category = "networks"
    page_name = 'cloud_tenant'
    string_name = 'CloudTenant'
    refresh_text = "Refresh items and relationships"
    detail_page_suffix = 'cloud_tenant_detail'
    quad_name = None
    db_types = ["CloudTenant"]

    name = attr.ib()


@attr.s
class CloudTenantCollection(BaseCollection):
    """ Collection object for CloudTenant object
        Note: Network providers object are not implemented in mgmt
    """
    ENTITY = CloudTenant


@navigator.register(CloudTenant, 'DetailsThroughProvider')
class TenantThroughProvider(CFMENavigateStep):
    prerequisite = NavigateToAttribute('provider_obj', 'CloudTenants')
    VIEW = CloudTenantDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(
            name=self.obj.name, surf_pages=True).click()
