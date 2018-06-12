import attr
from cached_property import cached_property
from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.exceptions import DestinationNotFound
from cfme.common import Taggable
from cfme.common.provider import BaseProvider, prepare_endpoints
from cfme.modeling.base import BaseCollection
from cfme.networks.balancer import BalancerCollection
from cfme.networks.cloud_network import CloudNetworkCollection
from cfme.networks.network_port import NetworkPortCollection
from cfme.networks.network_router import NetworkRouterCollection
from cfme.networks.security_group import SecurityGroupCollection
from cfme.networks.subnet import SubnetCollection
from cfme.networks.topology import NetworkTopologyView
from cfme.networks.views import (
    NetworkProviderDetailsView,
    NetworkProviderView,
    NetworkProviderAddView,
    OneProviderBalancerView,
    OneProviderCloudNetworkView,
    OneProviderNetworkPortView,
    OneProviderNetworkRouterView,
    OneProviderSecurityGroupView,
    OneProviderSubnetView,
    NetworkProviderEditView
)
from cfme.utils.providers import get_crud_by_name
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger


@attr.s(hash=False)
class NetworkProvider(BaseProvider, Taggable):
    """ Class representing network provider in sdn

    Note: Network provider can be added to cfme database
          only automaticaly with cloud provider
    """
    STATS_TO_MATCH = []
    string_name = 'Network'
    in_version = ('5.8', version.LATEST)
    edit_page_suffix = ''
    refresh_text = 'Refresh Relationships and Power States'
    quad_name = None
    category = 'networks'
    provider_types = {}
    property_tuples = []
    detail_page_suffix = 'provider_detail'
    db_types = ['NetworkManager']

    _collections = {
        'balancers': BalancerCollection,
        'cloud_networks': CloudNetworkCollection,
        'ports': NetworkPortCollection,
        'routers': NetworkRouterCollection,
        'subnets': SubnetCollection,
        'security_groups': SecurityGroupCollection,
    }

    name = attr.ib(default=None)
    provider = attr.ib(default=None)

    def __attrs_post_init__(self):
        self.parent = self.appliance.collections.network_providers

    @property
    def valid_credentials_state(self):
        """ Checks whether credentials are valid """
        view = navigate_to(self, 'Details')
        cred_state = view.entities.status.get_text_of('Default Credentials')
        return cred_state == "Valid"

    @cached_property
    def balancers(self):
        return self.collections.balancers

    @cached_property
    def subnets(self):
        return self.collections.subnets

    @cached_property
    def networks(self):
        return self.collections.cloud_networks

    @cached_property
    def ports(self):
        return self.collections.ports

    @cached_property
    def routers(self):
        return self.collections.routers

    @cached_property
    def security_groups(self):
        return self.collections.security_groups

    def create(self, cancel=False, validate_credentials=True, validate_inventory=False):
        created = True

        logger.info('Setting up Network Provider: %s', self.key)
        add_view = navigate_to(self, 'Add')

        if not cancel or (cancel and any(self.view_value_mapping.values())):
            # filling main part of dialog
            add_view.fill(self.view_value_mapping)

        if not cancel or (cancel and self.endpoints):
            # filling endpoints
            for endpoint_name, endpoint in self.endpoints.items():
                try:
                    # every endpoint class has name like 'default', 'events', etc.
                    # endpoints view can have multiple tabs, the code below tries
                    # to find right tab by passing endpoint name to endpoints view
                    endp_view = getattr(self.endpoints_form(parent=add_view),
                                        endpoint_name)
                except AttributeError:
                    # tabs are absent in UI when there is only single (default) endpoint
                    endp_view = self.endpoints_form(parent=add_view)

                endp_view.fill(endpoint.view_value_mapping)

                # filling credentials
                if hasattr(endpoint, 'credentials'):
                    endp_view.fill(endpoint.credentials.view_value_mapping)

                if (validate_credentials and hasattr(endp_view, 'validate') and
                        endp_view.validate.is_displayed):
                    # there are some endpoints which don't demand validation like
                    #  RSA key pair
                    endp_view.validate.click()
                    # Flash message widget is in add_view, not in endpoints tab
                    logger.info(
                        'Validating credentials flash message for endpoint %s',
                        endpoint_name)
                    self._post_validate_checks(add_view)

        main_view = self.create_view(navigator.get_class(self, 'All').VIEW)
        if cancel:
            created = False
            add_view.cancel.click()
            self._post_cancel_checks(main_view)
        else:
            add_view.add.click()
            self._post_create_checks(main_view, add_view)

        if validate_inventory:
            self.validate()

        return created

    def update(self, updates, cancel=False, validate_credentials=True):
        """
        Updates a provider in the UI.  Better to use utils.update.update context
        manager than call this directly.

        Args:
           updates (dict): fields that are changing.
           cancel (boolean): whether to cancel out of the update.
           validate_credentials (boolean): whether credentials have to be validated
        """
        edit_view = navigate_to(self, 'Edit')

        # filling main part of dialog
        endpoints = updates.pop('endpoints', None)
        if updates:
            edit_view.fill(updates)

        # filling endpoints
        if endpoints:
            endpoints = prepare_endpoints(endpoints)

            for endpoint in endpoints.values():
                # every endpoint class has name like 'default', 'events', etc.
                # endpoints view can have multiple tabs, the code below tries
                # to find right tab by passing endpoint name to endpoints view
                try:
                    endp_view = getattr(self.endpoints_form(parent=edit_view), endpoint.name)
                except AttributeError:
                    # tabs are absent in UI when there is only single (default) endpoint
                    endp_view = self.endpoints_form(parent=edit_view)
                endp_view.fill(endpoint.view_value_mapping)

                # filling credentials
                # the code below looks for existing endpoint equal to passed one and
                # compares their credentials. it fills passed credentials
                # if credentials are different
                cur_endpoint = self.endpoints[endpoint.name]
                if hasattr(endpoint, 'credentials'):
                    if not hasattr(cur_endpoint, 'credentials') or \
                            endpoint.credentials != cur_endpoint.credentials:
                        if hasattr(endp_view, 'change_password'):
                            endp_view.change_password.click()
                        elif hasattr(endp_view, 'change_key'):
                            endp_view.change_key.click()
                        else:
                            NotImplementedError(
                                "Such endpoint doesn't have change password/key button")

                        endp_view.fill(endpoint.credentials.view_value_mapping)
                if (validate_credentials and hasattr(endp_view, 'validate') and
                        endp_view.validate.is_displayed):
                    endp_view.validate.click()
                    self._post_validate_checks(edit_view)

        if cancel:
            edit_view.cancel.click()
            self._post_cancel_edit_checks()
        else:
            edit_view.save.click()
            if endpoints:
                for endp_name, endp in endpoints.items():
                    self.endpoints[endp_name] = endp
            if updates:
                self.name = updates.get('name', self.name)

            self._post_update_checks(edit_view)

    def _post_validate_checks(self, add_view):
        add_view.flash.assert_no_error()
        add_view.flash.assert_success_message(
            'Credential validation was successful')

    def _post_cancel_checks(self, main_view):
        main_view.flash.assert_no_error()
        cancel_text = ('Add of {} Manager was '
                       'cancelled by the user'.format(self.string_name))
        main_view.flash.assert_message(cancel_text)

    def _post_cancel_edit_checks(self):
        main_view = self.create_view(navigator.get_class(self, 'All').VIEW)
        main_view.flash.assert_no_error()
        cancel_text = ('Edit of {} Manager was '
                       'cancelled by the user'.format(self.string_name))
        main_view.flash.assert_message(cancel_text)

    def _post_create_checks(self, main_view, add_view=None):
        main_view.flash.assert_no_error()
        if main_view.is_displayed:
            success_text = '{} Providers "{}" was saved'.format(self.string_name, self.name)
            main_view.flash.assert_message(success_text)
        else:
            add_view.flash.assert_no_error()
            raise AssertionError("Provider wasn't added. It seems form isn't accurately filled")

    def _post_update_checks(self, edit_view):
        details_view = self.create_view(navigator.get_class(self, 'Details').VIEW)
        main_view = self.create_view(navigator.get_class(self, 'All').VIEW)
        main_view.flash.assert_no_error()
        success_text = '{} Manager "{}" was saved'.format(self.string_name, self.name)
        if main_view.is_displayed:
            main_view.flash.assert_message(success_text)
        elif details_view.is_displayed:
            details_view.flash.assert_message(success_text)
        else:
            edit_view.flash.assert_no_error()
            raise AssertionError("Provider wasn't updated. It seems form isn't accurately filled")

    def delete(self, cancel=True):
        """
        Deletes a provider from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove this Network Provider from Inventory',
                                               handle_alert=not cancel)
        if not cancel:
            msg = ('Delete initiated for 1 Network Provider from the {} Database'.format(
                self.appliance.product_name))
            view.flash.assert_success_message(msg)


@attr.s
class NetworkProviderCollection(BaseCollection):
    """Collection object for NetworkProvider object
       Note: Network providers object are not implemented in mgmt
    """

    ENTITY = NetworkProvider

    def all(self):
        view = navigate_to(self, 'All')
        list_networks = view.entities.get_all(surf_pages=True)
        network_providers = []

        if 'provider' in self.filters:
            for item in list_networks:
                if self.filters.get('provider').name in item.name:
                    network_providers.append(self.instantiate(name=item.name,
                                    provider=self.filters.get('provider')))
        else:
            for item in list_networks:
                provider = get_crud_by_name(item.name.split()[0])
                network_providers.append(self.instantiate(name=item.name, provider=provider))

        return network_providers

    def create(self, prov_class, *args, **kwargs):
        # ugly workaround until I move everything to main class
        class_attrs = [at.name for at in attr.fields(prov_class)]
        init_kwargs = {}
        create_kwargs = {}
        for name, value in kwargs.items():
            if name not in class_attrs:
                create_kwargs[name] = value
            else:
                init_kwargs[name] = value

        obj = self.instantiate(prov_class, *args, **init_kwargs)
        obj.create(**create_kwargs)
        return obj


@navigator.register(NetworkProvider, 'All')  # To be removed once all CEMv3
@navigator.register(NetworkProviderCollection, 'All')
class All(CFMENavigateStep):
    VIEW = NetworkProviderView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Providers')


@navigator.register(NetworkProvider, 'Add')  # To be removed once all CEMv3
@navigator.register(NetworkProviderCollection, 'Add')
class Add(CFMENavigateStep):
    VIEW = NetworkProviderAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a New '
                                                                 'Network Provider')


@navigator.register(NetworkProvider, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = NetworkProviderDetailsView

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name).click()


@navigator.register(NetworkProvider, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = NetworkProviderEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).check()
        self.prerequisite_view.toolbar.configuration.item_select('Edit Selected Network Provider')


@navigator.register(NetworkProvider, 'CloudSubnets')
class OpenCloudSubnets(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = OneProviderSubnetView

    def step(self):
        item = 'Cloud Subnets'
        item_amt = int(self.prerequisite_view.entities.relationships.get_text_of(item))
        if item_amt > 0:
            self.prerequisite_view.entities.relationships.click_at(item)
        else:
            raise DestinationNotFound("This provider doesn't have {item}".format(item=item))


@navigator.register(NetworkProvider, 'CloudNetworks')
class OpenCloudNetworks(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = OneProviderCloudNetworkView

    def step(self):
        item = 'Cloud Networks'
        item_amt = int(self.prerequisite_view.entities.relationships.get_text_of(item))
        if item_amt > 0:
            self.prerequisite_view.entities.relationships.click_at(item)
        else:
            raise DestinationNotFound("This provider doesn't have {item}".format(item=item))


@navigator.register(NetworkProvider, 'NetworkRouters')
class OpenNetworkRouters(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = OneProviderNetworkRouterView

    def step(self):
        item = 'Network Routers'
        item_amt = int(self.prerequisite_view.entities.relationships.get_text_of(item))
        if item_amt > 0:
            self.prerequisite_view.entities.relationships.click_at(item)
        else:
            raise DestinationNotFound("This provider doesn't have {item}".format(item=item))


@navigator.register(NetworkProvider, 'SecurityGroups')
class OpenSecurityGroups(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = OneProviderSecurityGroupView

    def step(self):
        item = 'Security Groups'
        item_amt = int(self.prerequisite_view.entities.relationships.get_text_of(item))
        if item_amt > 0:
            self.prerequisite_view.entities.relationships.click_at(item)
        else:
            raise DestinationNotFound("This provider doesn't have {item}".format(item=item))


@navigator.register(NetworkProvider, 'FloatingIPs')
class OpenFloatingIPs(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        item = 'Floating IPs'
        item_amt = int(self.prerequisite_view.entities.relationships.get_text_of(item))
        if item_amt > 0:
            self.prerequisite_view.entities.relationships.click_at(item)
        else:
            raise DestinationNotFound("This provider doesn't have {item}".format(item=item))


@navigator.register(NetworkProvider, 'NetworkPorts')
class OpenNetworkPorts(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = OneProviderNetworkPortView

    def step(self):
        item = 'Network Ports'
        item_amt = int(self.prerequisite_view.entities.relationships.get_text_of(item))
        if item_amt > 0:
            self.prerequisite_view.entities.relationships.click_at(item)
        else:
            raise DestinationNotFound("This provider doesn't have {item}".format(item=item))


@navigator.register(NetworkProvider, 'LoadBalancers')
class OpenNetworkBalancers(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = OneProviderBalancerView

    def step(self):
        item = 'Load Balancers'
        item_amt = int(self.prerequisite_view.entities.relationships.get_text_of(item))
        if item_amt > 0:
            self.prerequisite_view.entities.relationships.click_at(item)
        else:
            raise DestinationNotFound("This provider doesn't have {item}".format(item=item))


@navigator.register(NetworkProvider, 'TopologyFromDetails')
class OpenTopologyFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = NetworkTopologyView

    def step(self):
        self.prerequisite_view.entities.overview.click_at('Topology')
