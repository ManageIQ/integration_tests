""" A model of a Cloud Provider in CFME
"""
import fauxfactory

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_manageiq import TimelinesView, BreadCrumb, ItemsToolBarViewSelector
from widgetastic.exceptions import MoveTargetOutOfBoundsException
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown
from widgetastic.utils import partial_match

from cfme.exceptions import FlavorNotFound
from cfme.base.login import BaseLoggedInPage
from cfme.common import TagPageView
from cfme.common.provider import CloudInfraProvider
from cfme.common.provider_views import (
    CloudProviderAddView, CloudProviderEditView, CloudProviderDetailsView, CloudProvidersView,
    CloudProvidersDiscoverView)
from cfme.common.vm_views import VMToolbar, VMEntities
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.wait import wait_for


class CloudProviderTimelinesView(TimelinesView, BaseLoggedInPage):
    breadcrumb = BreadCrumb()

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'] and
            '{} (Summary)'.format(self.context['object'].name) in self.breadcrumb.locations and
            self.is_timelines)


class CloudProviderInstancesView(BaseLoggedInPage):
    """
    The collection page for provider instances
    """
    @property
    def is_displayed(self):
        return (
            self.breadcrumb.locations[0] == 'Cloud Providers' and
            self.entities.title.text == '{} (All Instances)'.format(self.context['object'].name))

    breadcrumb = BreadCrumb()
    toolbar = View.nested(VMToolbar)
    including_entities = View.include(VMEntities, use_parent=True)


class CloudProviderImagesToolbar(View):
    """
    Toolbar view for cloud provider images relationships
    """
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class CloudProviderImagesView(BaseLoggedInPage):
    """
    The collection page for provider images
    """
    @property
    def is_displayed(self):
        return (
            self.breadcrumb.locations[0] == 'Cloud Providers' and
            self.entities.title.text == '{} (All Images)'.format(self.context['object'].name))

    breadcrumb = BreadCrumb()
    toolbar = View.nested(CloudProviderImagesToolbar)
    including_entities = View.include(VMEntities, use_parent=True)


class CloudProvider(Pretty, CloudInfraProvider):
    """
    Abstract model of a cloud provider in cfme. See EC2Provider or OpenStackProvider.

    Args:
        name: Name of the provider.
        endpoints: one or several provider endpoints like DefaultEndpoint. it should be either dict
        in format dict{endpoint.name, endpoint, endpoint_n.name, endpoint_n}, list of endpoints or
        mere one endpoint
        key: The CFME key of the provider in the yaml.

    Usage:

        credentials = Credential(principal='bad', secret='reallybad')
        endpoint = DefaultEndpoint(hostname='some_host', region='us-west', credentials=credentials)
        myprov = VMwareProvider(name='foo',
                             endpoints=endpoint)
        myprov.create()
    """
    provider_types = {}
    category = "cloud"
    pretty_attrs = ['name', 'credentials', 'zone', 'key']
    STATS_TO_MATCH = ['num_template', 'num_vm']
    string_name = "Cloud"
    templates_destination_name = "Images"
    vm_name = "Instances"
    template_name = "Images"
    db_types = ["CloudManager"]

    def __init__(self, name=None, endpoints=None, zone=None, key=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.zone = zone
        self.key = key
        self.endpoints = self._prepare_endpoints(endpoints)

    def as_fill_value(self):
        return self.name

    @property
    def view_value_mapping(self):
        """Maps values to view attrs"""
        return {'name': self.name}

    @staticmethod
    def discover_dict(credential):
        """Returns the discovery credentials dictionary, needs overiding"""
        raise NotImplementedError("This provider doesn't support discovery")

    @property
    def vm_default_args(self):
        """
        Represents dictionary used for Vm/Instance provision with minimum required default args
        """
        provisioning = self.data['provisioning']
        inst_args = {
            'request': {'email': 'vm_provision@cfmeqe.com'},
            'catalog': {
                'vm_name': 'test-'.format(fauxfactory.gen_alphanumeric(5))},
            'environment': {
                'availability_zone': provisioning.get('availability_zone'),
                'cloud_network': provisioning.get('cloud_network'),
                'cloud_subnet': provisioning.get('cloud_subnet'),
                'resource_groups': provisioning.get('resource_group')
            },
            'properties': {
                'instance_type': partial_match(provisioning.get('instance_type')),
                'guest_keypair': provisioning.get('guest_keypair')}
        }

        return inst_args

    @property
    def vm_default_args_rest(self):
        """
        Represents dictionary used for REST API Vm/Instance provision with minimum required default
        args
        """
        from cfme.cloud.provider.azure import AzureProvider
        from cfme.cloud.provider.ec2 import EC2Provider
        from cfme.cloud.provider.gce import GCEProvider

        if not self.is_refreshed():
            self.refresh_provider_relationships()
            wait_for(self.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
        provisioning = self.data['provisioning']
        image_guid = self.appliance.rest_api.collections.templates.find_by(
            name=provisioning['image']['name'])[0].guid
        if ':' in provisioning['instance_type'] and self.one_of(EC2Provider, GCEProvider):
            instance_type = provisioning['instance_type'].split(':')[0].strip()
        elif self.one_of(AzureProvider):
            instance_type = provisioning['instance_type'].lower()
        else:
            instance_type = provisioning['instance_type']

        flavors = self.appliance.rest_api.collections.flavors.find_by(name=instance_type)
        assert flavors, "Flavor {} wasn't found"
        for flavor in flavors:
            try:
                ems_id = flavor.ems_id
            except AttributeError:
                    continue
            if ems_id == self.id and flavor.ems.name == self.name:
                flavor_id = flavor.id
                break
        else:
            raise FlavorNotFound("Cannot find flavour {} for provider {}".
                                 format(instance_type, self.name))

        inst_args = {
            "version": "1.1",
            "template_fields": {
                "guid": image_guid,
            },
            "vm_fields": {
                "vm_name": 'test-'.format(fauxfactory.gen_alphanumeric(5)),
                "instance_type": flavor_id,
                "request_type": "template",
            },
            "requester": {
                "user_name": "admin",
                "owner_email": "admin@cfmeqe.com",
                "auto_approve": True,
            },
            "tags": {
            },
            "additional_values": {
                # 'placement_auto' defaults to True if not specified
                # "placemnet_auto": True
            },
            "ems_custom_attributes": {
            },
            "miq_custom_attributes": {
            }
        }

        return inst_args


@navigator.register(CloudProvider, 'All')
class All(CFMENavigateStep):
    VIEW = CloudProvidersView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Providers')

    def resetter(self):
        self.appliance.browser.widgetastic.browser.refresh()
        tb = self.view.toolbar
        if 'Grid View' not in tb.view_selector.selected:
            tb.view_selector.select('Grid View')
        self.view.entities.paginator.reset_selection()


@navigator.register(CloudProvider, 'Add')
class New(CFMENavigateStep):
    VIEW = CloudProviderAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a New Cloud Provider')


@navigator.register(CloudProvider, 'Discover')
class Discover(CFMENavigateStep):
    VIEW = CloudProvidersDiscoverView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Discover Cloud Providers')


@navigator.register(CloudProvider, 'Details')
class Details(CFMENavigateStep):
    VIEW = CloudProviderDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(CloudProvider, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = CloudProviderEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).check()
        try:
            self.prerequisite_view.toolbar.configuration.item_select('Edit Selected Cloud Provider')
        except MoveTargetOutOfBoundsException:
            # TODO: Remove once fixed 1475303
            self.prerequisite_view.toolbar.configuration.item_select('Edit Selected Cloud Provider')


@navigator.register(CloudProvider, 'EditFromDetails')
class EditFromDetails(CFMENavigateStep):
    VIEW = CloudProviderEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Cloud Provider')


@navigator.register(CloudProvider, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).check()
        try:
            self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
        except MoveTargetOutOfBoundsException:
            # TODO: Remove once fixed 1475303
            self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(CloudProvider, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = CloudProviderTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        mon = self.prerequisite_view.toolbar.monitoring
        try:
            mon.item_select('Timelines')
        except MoveTargetOutOfBoundsException:
            # TODO: Remove once fixed 1475303
            mon.item_select('Timelines')


@navigator.register(CloudProvider, 'Instances')
class Instances(CFMENavigateStep):
    VIEW = CloudProviderInstancesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.summary("Relationships").click_at('Instances')


@navigator.register(CloudProvider, 'Images')
class Images(CFMENavigateStep):
    VIEW = CloudProviderImagesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.summary("Relationships").click_at('Images')


def get_all_providers():
    """Returns list of all providers"""
    view = navigate_to(CloudProvider, 'All')
    return [item.name for item in view.entities.get_all(surf_pages=True)]


def discover(credential, discover_cls, cancel=False):
    """
    Discover cloud providers. Note: only starts discovery, doesn't
    wait for it to finish.

    Args:
      credential (cfme.base.credential.Credential):  Discovery credentials.
      cancel (boolean):  Whether to cancel out of the discover UI.
      discover_cls: class of the discovery item
    """
    view = navigate_to(CloudProvider, 'Discover')
    if discover_cls:
        view.fill({'discover_type': discover_cls.discover_name})
        view.fields.fill(discover_cls.discover_dict(credential))

    if cancel:
        view.cancel.click()
    else:
        view.start.click()


def wait_for_a_provider():
    view = navigate_to(CloudProvider, 'All')
    logger.info('Waiting for a provider to appear...')
    wait_for(lambda: int(view.entities.paginator.items_amount), fail_condition=0,
             message="Wait for any provider to appear", num_sec=1000,
             fail_func=view.browser.refresh)
