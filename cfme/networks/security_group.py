import attr

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.networks.views import SecurityGroupDetailsView, SecurityGroupView, SecurityGroupAddView
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.wait import wait_for


@attr.s
class SecurityGroup(WidgetasticTaggable, BaseEntity):
    """Class representing security group in sdn"""
    in_version = ('5.8', version.LATEST)
    category = 'networks'
    page_name = 'security_group'
    string_name = 'SecurityGroup'
    quad_name = None
    db_types = ['SecurityGroup']

    name = attr.ib()

    @property
    def provider(self):
        from cfme.networks.provider import NetworkProvider
        return parent_of_type(self, NetworkProvider)

    @property
    def network_provider(self):
        """ Returns network provider """
        # security group collection contains reference to provider
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
class SecurityGroupCollection(BaseCollection):
    """ Collection object for SecurityGroup object
        Note: Network providers object are not implemented in mgmt
    """
    ENTITY = SecurityGroup

    def all(self):
        if self.filters.get('parent'):
            view = navigate_to(self.filters.get('parent'), 'SecurityGroups')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=s.name) for s in list_networks_obj]

    def create(self, name, tenant, network_manager, description, provider):
        view = navigate_to(self, 'Add')
        view.fill({'network_manager': network_manager,
                   'group_name': name})
        # use description and tenant fill separately
        view.description.fill(description)
        view.cloud_tenant.select_by_visible_text(tenant)
        view.add.click()
        sec_group = self.instantiate(name)
        # Refresh provider's relationships to have new network displayed
        provider.refresh_provider_relationships()
        wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
        return sec_group

    def exists(self, group):
        groups = [r.name for r in self.all()]
        return group.name in groups


@navigator.register(SecurityGroupCollection, 'All')
class All(CFMENavigateStep):
    VIEW = SecurityGroupView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Security Groups')


@navigator.register(SecurityGroupCollection, 'Add')
class AddNewSecurityGroup(CFMENavigateStep):
    VIEW = SecurityGroupAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Add a new Security Group")


@navigator.register(SecurityGroup, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = SecurityGroupDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(surf_pages=True, name=self.obj.name).click()
