""" A model of a Cloud Provider in CFME
"""
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_manageiq import TimelinesView

from cfme.base.login import BaseLoggedInPage
from cfme.common import TagPageView
from cfme.common.provider_views import (CloudProviderAddView,
                                        CloudProviderEditView,
                                        CloudProviderDetailsView,
                                        CloudProvidersView,
                                        CloudProvidersDiscoverView,
                                        ProvidersManagePoliciesView
                                        )
import cfme.fixtures.pytest_selenium as sel
from cfme.common.provider import CloudInfraProvider
from cfme.web_ui import InfoBlock
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from cfme.utils.pretty import Pretty


class CloudProviderTimelinesView(TimelinesView, BaseLoggedInPage):
    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'] and \
            super(TimelinesView, self).is_displayed


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
    page_name = "clouds"
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


@navigator.register(CloudProvider, 'All')
class All(CFMENavigateStep):
    VIEW = CloudProvidersView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Providers')

    def resetter(self):
        tb = self.view.toolbar
        paginator = self.view.entities.paginator
        if 'Grid View' not in tb.view_selector.selected:
            tb.view_selector.select('Grid View')
        if paginator.exists:
            paginator.check_all()
            paginator.uncheck_all()


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
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name, surf_pages=True).click()


@navigator.register(CloudProvider, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = CloudProviderEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name, surf_pages=True).check()
        self.prerequisite_view.toolbar.configuration.item_select('Edit Selected Cloud Provider')


@navigator.register(CloudProvider, 'EditFromDetails')
class EditFromDetails(CFMENavigateStep):
    VIEW = CloudProviderEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Cloud Provider')


@navigator.register(CloudProvider, 'ManagePolicies')
class ManagePolicies(CFMENavigateStep):
    VIEW = ProvidersManagePoliciesView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name, surf_pages=True).check()
        self.prerequisite_view.toolbar.policy.item_select('Manage Policies')


@navigator.register(CloudProvider, 'ManagePoliciesFromDetails')
class ManagePoliciesFromDetails(CFMENavigateStep):
    VIEW = ProvidersManagePoliciesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Manage Policies')


@navigator.register(CloudProvider, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name, surf_pages=True).check()
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(CloudProvider, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = CloudProviderTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        mon = self.prerequisite_view.toolbar.monitoring
        mon.item_select('Timelines')


@navigator.register(CloudProvider, 'Instances')
class Instances(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return self.entities.title.text == '{} (All Instances)'.format(self.obj.name)

    def step(self, *args, **kwargs):
        sel.click(InfoBlock.element('Relationships', 'Instances'))


@navigator.register(CloudProvider, 'Images')
class Images(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return self.entities.title.text == '{} (All Images)'.format(self.obj.name)

    def step(self, *args, **kwargs):
        sel.click(InfoBlock.element('Relationships', 'Images'))


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
