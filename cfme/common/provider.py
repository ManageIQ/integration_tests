import datetime
from collections import defaultdict
from collections.abc import Iterable

import attr
from manageiq_client.api import APIException
from varmeth import variable
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from cfme.base.credential import CANDUCredential
from cfme.base.credential import Credential
from cfme.base.credential import EventsCredential
from cfme.base.credential import SSHCredential
from cfme.base.credential import TokenCredential
from cfme.common import CustomButtonEventsMixin
from cfme.common import Taggable
from cfme.common.datastore_views import ProviderAllDatastoresView
from cfme.exceptions import AddProviderError
from cfme.exceptions import HostStatsNotContains
from cfme.exceptions import ProviderHasNoKey
from cfme.exceptions import ProviderHasNoProperty
from cfme.exceptions import RestLookupError
from cfme.modeling.base import BaseEntity
from cfme.utils import conf
from cfme.utils import ParamClassName
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.net import resolve_hostname
from cfme.utils.stats import tol_check
from cfme.utils.update import Updateable
from cfme.utils.version import VersionPicker
from cfme.utils.wait import RefreshTimer
from cfme.utils.wait import wait_for


_base_types_cache = {}
_provider_types_cache = defaultdict(dict)
_all_types_cache = {}


# TODO: Move to collection when it happens
def base_types():
    from pkg_resources import iter_entry_points
    if not _base_types_cache:
        _base_types_cache.update({
            ep.name: ep.resolve() for ep in iter_entry_points('manageiq.provider_categories')
        })
    return _base_types_cache


# TODO: Move to collection when it happens
def provider_types(category):
    from pkg_resources import iter_entry_points
    if category not in _provider_types_cache:
        _provider_types_cache[category] = {
            ep.name: ep.resolve() for ep in iter_entry_points(
                f'manageiq.provider_types.{category}')
        }
    return _provider_types_cache[category]


# TODO: Move to collection when it happens
def all_types():
    if not _all_types_cache:
        _all_types_cache.update(base_types())
        for category in list(_all_types_cache):
            _all_types_cache.update(provider_types(category))
    return _all_types_cache


# TODO: Move to collection when it happens
def provider_db_mapping():
    return {v.db_types[0]: v for k, v in all_types().items()}


# todo: move to collections ?
def prepare_endpoints(endpoints):
    if endpoints is None:
        return {}
    elif isinstance(endpoints, dict):
        return endpoints
    elif isinstance(endpoints, Iterable):
        return {(e.name, e) for e in endpoints}
    elif isinstance(endpoints, DefaultEndpoint):
        return {endpoints.name: endpoints}
    else:
        raise ValueError("Endpoints should be either dict or endpoint class")


@attr.s(eq=False)
class BaseProvider(Taggable, Updateable, Navigatable, BaseEntity, CustomButtonEventsMixin):
    # List of constants that every non-abstract subclass must have defined

    # TODO: Navigatable is used to ensure function until the reduced get_crud is
    # replaced by methods on collections. This will be fixed in next conversion PR

    _param_name = ParamClassName('name')
    STATS_TO_MATCH = []
    db_types = ["Providers"]
    provisioning_dialog_widget_names = {'request', 'purpose', 'catalog', 'environment', 'schedule'}
    ems_events = []
    settings_key = None
    vm_class = None  # Set on type specific provider classes for VM/instance class
    template_class = None  # Set on type specific provider classes for VM template class
    ems_pretty_name = None  # Set on type specific provider classes for ems type selection in UI

    endpoints = attr.ib(default=attr.Factory(factory=dict))

    def __attrs_post_init__(self):
        # attr.ib(convert=prepare_endpoints) doesn't work correctly. this is workaround
        self.endpoints = prepare_endpoints(self.endpoints)

    def __hash__(self):
        return hash(self.key) ^ hash(type(self))

    def __eq__(self, other):
        return type(self) is type(other) and self.key == other.key

    def __str__(self):
        return self.name

    @property
    def data(self):
        """ Returns yaml data for this provider.
        """
        if hasattr(self, 'provider_data') and self.provider_data is not None:
            return self.provider_data
        elif self.key is not None:
            return conf.cfme_data['management_systems'][self.key]
        else:
            raise ProviderHasNoKey(
                f'Provider {self.name} has no key, so cannot get yaml data')

    @property
    def mgmt(self):
        """ Returns the mgmt_system using the :py:func:`utils.providers.get_mgmt` method.
        """
        # gotta stash this in here to prevent circular imports
        from cfme.utils.providers import get_mgmt

        if self.key:
            return get_mgmt(self.key)
        elif getattr(self, 'provider_data', None):
            return get_mgmt(self.provider_data)
        else:
            raise ProviderHasNoKey(
                f'Provider {self.name} has no key, so cannot get mgmt system')

    @property
    def type(self):
        return self.type_name

    @property
    def rest_api_entity(self):
        try:
            return self.appliance.rest_api.collections.providers.get(name=self.name)
        except (ValueError, APIException):
            raise RestLookupError(f'No provider rest entity found matching name {self.name}')

    @property
    def id(self):
        """"
        Return the ID associated with the specified provider name
        """
        return self.rest_api_entity.id

    @property
    def version(self):
        return self.data['version']

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines and usually overidden"""
        return {}

    @property
    def default_endpoint(self):
        return self.endpoints.get('default') if hasattr(self, 'endpoints') else None

    def create(self, cancel=False, validate_credentials=True, check_existing=False,
               validate_inventory=False):
        """
        Creates a provider in the UI

        Args:
            cancel (boolean): Whether to cancel out of the creation.  The cancel is done
                after all the information present in the Provider has been filled in the UI.
            validate_credentials (boolean): Whether to validate credentials - if True and the
                credentials are invalid, an error will be raised.
            check_existing (boolean): Check if this provider already exists, skip if it does
            validate_inventory (boolean): Whether or not to block until the provider stats in CFME
                match the stats gleaned from the backend management system

        Returns:
            True if it was created, False if it already existed
        """
        if check_existing and self.exists:
            created = False
        else:
            created = True
            logger.info('Setting up Provider: %s', self.key)
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
                    # sometimes we have cases that we need to validate even though
                    # there is no credentials, such as Hawkular endpoint
                    if (validate_credentials and hasattr(endp_view, 'validate') and
                            endp_view.validate.is_displayed):
                        # there are some endpoints which don't demand validation like
                        #  RSA key pair
                        endp_view.validate.click()
                        # Flash message widget is in add_view, not in endpoints tab
                        logger.info(
                            'Validating credentials flash message for endpoint %s',
                            endpoint_name)
                        add_view.flash.assert_no_error()
                        add_view.flash.assert_success_message(
                            'Credential validation was successful')

            main_view = self.create_view(navigator.get_class(self, 'All').VIEW)
            if cancel:
                created = False
                add_view.cancel.click()
                main_view.flash.assert_no_error()
            else:
                add_view.add.click()
                if main_view.is_displayed:
                    main_view.flash.assert_no_error()
                else:
                    add_view.flash.assert_no_error()
                    raise AssertionError("Provider wasn't added. It seems form isn't accurately"
                                         " filled")

        if validate_inventory:
            self.validate()

        return created

    def _fill_provider_attributes(self, provider_attributes):
        """Fills provider data.

        Helper method for ``self.create_rest``
        """
        if getattr(self, "region", None):
            if isinstance(self.region, dict):
                provider_attributes["provider_region"] = VersionPicker(self.region).pick(
                    self.appliance.version)
            else:
                provider_attributes["provider_region"] = self.region

        if getattr(self, "project", None):
            provider_attributes["project"] = self.project

        if getattr(self, "tenant_mapping", None):
            provider_attributes["tenant_mapping_enabled"] = self.tenant_mapping

        if self.type_name in ('openstack_infra', 'openstack'):
            if getattr(self, 'api_version', None):
                version = 'v3' if 'v3' in self.api_version else 'v2'
                provider_attributes['api_version'] = version
                if version == 'v3' and getattr(self, 'keystone_v3_domain_id', None):
                    provider_attributes['uid_ems'] = self.keystone_v3_domain_id

        if self.type_name == "azure":
            provider_attributes["azure_tenant_id"] = self.tenant_id
            provider_attributes["provider_region"] = self.region.lower().replace(" ", "")
            if getattr(self, "subscription_id", None):
                provider_attributes["subscription"] = self.subscription_id

    def _fill_default_endpoint_dicts(self, provider_attributes, connection_configs):
        """Fills dicts with default endpoint data.

        Helper method for ``self.create_rest``
        """
        default_connection = {
            "endpoint": {"role": "default"}
        }

        endpoint_default = self.endpoints["default"]

        from cfme.containers.provider.openshift import OpenshiftProvider

        if self.one_of(OpenshiftProvider) and getattr(endpoint_default.credentials, "token", None):
            default_connection["authentication"] = {"auth_key": endpoint_default.credentials.token}
        elif getattr(endpoint_default.credentials, "principal", None):
            provider_attributes["credentials"] = {
                "userid": endpoint_default.credentials.principal,
                "password": endpoint_default.credentials.secret,
            }
        elif getattr(endpoint_default.credentials, "service_account", None):
            default_connection["authentication"] = {
                "type": "AuthToken",
                "auth_type": "default",
                "auth_key": endpoint_default.credentials.service_account,
            }
        else:
            raise AssertionError("Provider wasn't added. "
                "No credentials info found for provider {}.".format(self.name))

        if hasattr(endpoint_default, "ca_certs"):
            default_connection["endpoint"]["certificate_authority"] = endpoint_default.ca_certs

        if hasattr(endpoint_default, "verify_tls"):
            default_connection["endpoint"]["verify_ssl"] = 1 if endpoint_default.verify_tls else 0

        if getattr(endpoint_default, "api_port", None):
            default_connection["endpoint"]["port"] = endpoint_default.api_port

        sec_protocol = getattr(endpoint_default, "security_protocol", None) or getattr(
            endpoint_default, "sec_protocol", None
        )
        if sec_protocol:
            security_protocol = sec_protocol.lower()
            if security_protocol in ('basic (ssl)', 'ssl without validation'):
                if self.one_of(OpenshiftProvider) and security_protocol == "ssl without validation":
                    security_protocol = "ssl-without-validation"
                else:
                    security_protocol = "ssl"
            elif security_protocol == "ssl":
                security_protocol = 'ssl-with-validation'

            default_connection["endpoint"]["security_protocol"] = security_protocol

        connection_configs.append(default_connection)

    def _fill_candu_endpoint_dicts(self, provider_attributes, connection_configs):
        """Fills dicts with candu endpoint data.

        Helper method for ``self.create_rest``
        """
        if "candu" not in self.endpoints:
            return

        endpoint_candu = self.endpoints["candu"]
        if isinstance(provider_attributes["credentials"], dict):
            provider_attributes["credentials"] = [provider_attributes["credentials"]]
        provider_attributes["credentials"].append({
            "userid": endpoint_candu.credentials.principal,
            "password": endpoint_candu.credentials.secret,
            "auth_type": "metrics",
        })
        candu_connection = {
            "endpoint": {
                "hostname": endpoint_candu.hostname,
                "path": endpoint_candu.database,
                "role": "metrics",
            },
        }
        if getattr(endpoint_candu, "api_port", None):
            candu_connection["endpoint"]["port"] = endpoint_candu.api_port
        if hasattr(endpoint_candu, "verify_tls") and not endpoint_candu.verify_tls:
            candu_connection["endpoint"]["verify_ssl"] = 0
        connection_configs.append(candu_connection)

    def _fill_rsa_endpoint_dicts(self, connection_configs):
        """Fills dicts with rsa endpoint data.

        Helper method for ``self.create_rest``
        """
        if "rsa_keypair" not in self.endpoints:
            return

        endpoint_rsa = self.endpoints["rsa_keypair"].credentials
        connection_configs.append(
            {
                "authentication": {
                    "userid": endpoint_rsa.principal,
                    "auth_key": endpoint_rsa.secret,
                },
                "endpoint": {"role": "ssh_keypair"}
            }
        )

    def _fill_amqp_endpoint_dicts(self, provider_attributes, connection_configs):
        """Fills dicts with AMQP events endpoint data.

        Helper method for ``self.create_rest``
        """
        if "events" not in self.endpoints:
            return

        endpoint_events = self.endpoints["events"]

        event_stream = getattr(endpoint_events, "event_stream", None)
        if not (event_stream and event_stream.lower() == "amqp"):
            return

        if isinstance(provider_attributes["credentials"], dict):
            provider_attributes["credentials"] = [provider_attributes["credentials"]]
        provider_attributes["credentials"].append(
            {
                "userid": endpoint_events.credentials.principal,
                "password": endpoint_events.credentials.secret,
                "auth_type": "amqp",
            }
        )
        events_connection = {
            "endpoint": {"hostname": endpoint_events.hostname, "role": "amqp"}
        }
        if getattr(endpoint_events, "api_port", None):
            events_connection["endpoint"]["port"] = endpoint_events.api_port
        if getattr(endpoint_events, "security_protocol", None):
            security_protocol = endpoint_events.security_protocol.lower()
            events_connection["endpoint"]["security_protocol"] = security_protocol
        connection_configs.append(events_connection)

    def _fill_ceilometer_endpoint_dicts(self, provider_attributes, connection_configs):
        """Fills dicts with Ceilometer events endpoint data.

        Helper method for ``self.create_rest``
        """
        if 'events' not in self.endpoints:
            return

        endpoint_events = self.endpoints['events']

        event_stream = getattr(endpoint_events, 'event_stream', None)
        if not (event_stream and event_stream.lower() == 'ceilometer'):
            return

        events_connection = {
            'endpoint': {'role': 'ceilometer'}
        }
        connection_configs.append(events_connection)

    def _fill_smartstate_endpoint_dicts(self, provider_attributes):
        """Fills dicts with smartstate endpoint data.

        Helper method for ``self.create_rest``
        """
        if "smartstate" not in self.endpoints:
            return

        endpoint_rsa = self.endpoints["smartstate"]
        if isinstance(provider_attributes["credentials"], dict):
            provider_attributes["credentials"] = [provider_attributes["credentials"]]

        provider_attributes["credentials"].append({
            "userid": endpoint_rsa.credentials.principal,
            "password": endpoint_rsa.credentials.secret,
            "auth_type": "smartstate_docker",
        })

    def _fill_vmrc_console_endpoint_dicts(self, provider_attributes):
        """Fills dicts with VMRC console endpoint data

        Helper method for ``self.create_rest``
        """
        if "vmrc" not in self.endpoints:
            return

        endpoints_vmrc = self.endpoints["vmrc"]
        if isinstance(provider_attributes["credentials"], dict):
            provider_attributes["credentials"] = [provider_attributes["credentials"]]

        provider_attributes["credentials"].append(
            {
                "auth_type": "console",
                "userid": endpoints_vmrc.credentials.principal,
                "password": endpoints_vmrc.credentials.secret,
            }
        )

    def _fill_hawkular_endpoint_dicts(self, connection_configs):
        """Fills dicts with hawkular endpoint data.

        Helper method for ``self.create_rest``
        """
        if "metrics" not in self.endpoints:
            return

        endpoint_hawkular = self.endpoints["metrics"]

        hawkular_connection = {
            "endpoint": {
                "hostname": endpoint_hawkular.hostname,
                "role": "hawkular",
            },
        }
        if getattr(endpoint_hawkular, "api_port", None):
            hawkular_connection["endpoint"]["port"] = endpoint_hawkular.api_port

        if getattr(endpoint_hawkular, "sec_protocol", None):
            security_protocol = endpoint_hawkular.sec_protocol.lower()
            if security_protocol == 'ssl without validation':
                security_protocol = "ssl-without-validation"
            elif security_protocol == "ssl":
                security_protocol = 'ssl-with-validation'

            hawkular_connection["endpoint"]["security_protocol"] = security_protocol

        connection_configs.append(hawkular_connection)

    def _compile_connection_configurations(self, provider_attributes, connection_configs):
        """Compiles together all dicts with data for ``connection_configurations``.

        Helper method for ``self.create_rest``
        """
        provider_attributes["connection_configurations"] = []
        appended = []
        for config in connection_configs:
            role = config["endpoint"]["role"]
            if role not in appended:
                provider_attributes["connection_configurations"].append(config)
                appended.append(role)

    def create_rest(self, check_existing=False, validate_inventory=False):
        """
        Creates a provider using REST

        Args:
            check_existing (boolean): Check if this provider already exists, skip if it does
            validate_inventory (boolean): Whether or not to block until the provider stats in CFME
                match the stats gleaned from the backend management system

        Returns:
            True if it was created, False if it already existed
        """
        if check_existing and self.exists:
            return False

        logger.info("Setting up provider via REST: %s", self.key)

        # provider attributes
        provider_attributes = {
            "hostname": self.hostname,
            "ipaddress": self.ip_address,
            "name": self.name,
            "type": f"ManageIQ::Providers::{self.db_types[0]}",
        }

        # data for provider_attributes['connection_configurations']
        connection_configs = []

        # produce final provider_attributes
        self._fill_provider_attributes(provider_attributes)
        self._fill_default_endpoint_dicts(provider_attributes, connection_configs)
        self._fill_candu_endpoint_dicts(provider_attributes, connection_configs)
        self._fill_rsa_endpoint_dicts(connection_configs)
        self._fill_amqp_endpoint_dicts(provider_attributes, connection_configs)
        self._fill_ceilometer_endpoint_dicts(provider_attributes, connection_configs)
        self._fill_smartstate_endpoint_dicts(provider_attributes)
        self._fill_vmrc_console_endpoint_dicts(provider_attributes)
        self._fill_hawkular_endpoint_dicts(connection_configs)
        self._compile_connection_configurations(provider_attributes, connection_configs)

        try:
            self.appliance.rest_api.collections.providers.action.create(**provider_attributes)
        except APIException as err:
            raise AssertionError(f"Provider was not added: {err}")

        response = self.appliance.rest_api.response
        if not response:
            raise AssertionError(f"Provider was not added, status code {response.status_code}")

        if validate_inventory:
            self.validate(timeout=300)

        self.appliance.rest_api.response = response
        return True

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
        # todo: to replace/merge this code with create
        # update values:
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
                    if (not hasattr(cur_endpoint, 'credentials') or
                            endpoint.credentials != cur_endpoint.credentials):
                        if hasattr(endp_view, 'change_password'):
                            endp_view.change_password.click()
                        elif hasattr(endp_view, 'change_key'):
                            endp_view.change_key.click()
                        else:
                            NotImplementedError(
                                "Such endpoint doesn't have change password/key button")

                        endp_view.fill(endpoint.credentials.view_value_mapping)
                # sometimes we have cases that we need to validate even though
                # there is no credentials, such as Hawkular endpoint
                if (validate_credentials and hasattr(endp_view, 'validate') and
                        endp_view.validate.is_displayed):
                    endp_view.validate.click()

        # cloud rhos provider always requires validation of all endpoints
        # there should be a bz about that
        from cfme.cloud.provider.openstack import OpenStackProvider
        if self.one_of(OpenStackProvider):
            for endp in self.endpoints.values():
                endp_view = getattr(self.endpoints_form(parent=edit_view), endp.name)
                if hasattr(endp_view, 'validate') and endp_view.validate.is_displayed:
                    endp_view.validate.click()

        details_view = self.create_view(navigator.get_class(self, 'Details').VIEW)
        main_view = self.create_view(navigator.get_class(self, 'All').VIEW)

        if cancel:
            edit_view.cancel.click()
            cancel_text = 'Edit of {type} Provider "{name}" ' \
                          'was cancelled by the user'.format(type=self.string_name,
                                                             name=self.name)
            main_view.flash.assert_message(cancel_text)
            main_view.flash.assert_no_error()
        else:
            edit_view.save.click()
            if endpoints:
                for endp_name, endp in endpoints.items():
                    self.endpoints[endp_name] = endp
            if updates:
                self.name = updates.get('name', self.name)

            success_text = f'{self.string_name} Provider "{self.name}" was saved'
            if main_view.is_displayed:
                # since 5.8.1 main view is displayed when edit starts from main view
                main_view.flash.assert_message(success_text)
            elif details_view.is_displayed:
                # details view is always displayed up to 5.8.1
                details_view.flash.assert_message(success_text)
            else:
                edit_view.flash.assert_no_error()
                raise AssertionError("Provider wasn't updated. It seems form isn't accurately"
                                     " filled")

    def delete(self, cancel=False):
        """
        Deletes a provider from CFME using UI

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """
        view = navigate_to(self, 'Details')
        item_title = 'Remove this {} Provider from Inventory'
        view.toolbar.configuration.item_select(item_title.format(self.string_name),
                                               handle_alert=not cancel)
        if not cancel:
            main_view = self.create_view(navigator.get_class(self, 'All').VIEW, wait='10s')
            main_view.flash.assert_no_error()

    def delete_rest(self):
        """Deletes a provider from CFME using REST"""
        try:
            self.rest_api_entity.action.delete()
        except APIException as err:
            raise AssertionError(f"Provider wasn't deleted: {err}")

        response = self.appliance.rest_api.response
        if not response:
            raise AssertionError("Provider wasn't deleted, status code {}".format(
                response.status_code))

    def setup(self):
        """
        Sets up the provider robustly
        """
        # TODO: Eventually this will become Sentakuified, but only after providers is CEMv3
        return self.create_rest(check_existing=True, validate_inventory=True)

    @variable(alias='rest')
    def is_refreshed(self, refresh_timer=None, refresh_delta=600, force_refresh=True):
        if refresh_timer:
            if refresh_timer.is_it_time():
                logger.info(' Time for a refresh!')
                self.refresh_provider_relationships()
                refresh_timer.reset()
        rdate = self.last_refresh_date()
        if not rdate:
            return False
        td = self.appliance.utc_time() - rdate
        if td > datetime.timedelta(0, refresh_delta):
            if force_refresh:
                self.refresh_provider_relationships()
            return False
        else:
            return True

    def validate(self, timeout=1000, delay=5):
        refresh_timer = RefreshTimer(time_for_refresh=300)
        try:
            wait_for(self.is_refreshed,
                     [refresh_timer],
                     message="is_refreshed",
                     timeout=timeout,
                     delay=delay,
                     handle_exception=True)
        except Exception:
            # To see the possible error.
            self.load_details(refresh=True)
            raise
        else:
            if self.last_refresh_error() is not None:
                raise AddProviderError("Cannot validate the provider. Error occured: {}".format(
                                       self.last_refresh_error()))

    def validate_stats(self, ui=False):
        """ Validates that the detail page matches the Providers information.

        This method logs into the provider using the mgmt_system interface and collects
        a set of statistics to be matched against the UI. The details page is then refreshed
        continuously until the matching of all items is complete. A error will be raised
        if the match is not complete within a certain defined time period.
        """

        # If we're not using db, make sure we are on the provider detail page
        if ui:
            self.load_details()

        # Initial bullet check
        if self._do_stats_match(self.mgmt, self.STATS_TO_MATCH, ui=ui):
            self.mgmt.disconnect()
            return
        else:
            # Set off a Refresh Relationships
            if self.category == "config_manager" and ui:
                self.refresh_relationships()
            else:
                method = 'ui' if ui else None
                self.refresh_provider_relationships(method=method)

            refresh_timer = RefreshTimer(time_for_refresh=300)
            wait_for(self._do_stats_match,
                     [self.mgmt, self.STATS_TO_MATCH, refresh_timer],
                     {'ui': ui},
                     message="do_stats_match_db",
                     num_sec=1000,
                     delay=60)

        self.mgmt.disconnect()

    @variable(alias='rest')
    def refresh_provider_relationships(self, from_list_view=False,
                                       wait=0, delay=1, refresh_delta=10):
        """
        wait[seconds], 0 for no wait
        """
        # from_list_view is ignored as it is included here for sake of compatibility with UI call.
        logger.debug('Refreshing provider relationships')
        name = self.ui_name if self.category == "config_manager" else self.name
        col = self.appliance.rest_api.collections.providers.find_by(name=name)
        try:
            col[0].action.refresh()
            self.wait_for_relationship_refresh(wait, delay, refresh_delta)
        except IndexError:
            raise LookupError("Provider collection empty")

    @refresh_provider_relationships.variant('ui')
    def refresh_provider_relationships_ui(self, from_list_view=False, wait=0, delay=1,
                                          refresh_delta=10):
        """Clicks on Refresh relationships button in provider"""
        if from_list_view:
            view = navigate_to(self, 'All')
            entity = view.entities.get_entity(name=self.name, surf_pages=True)
            entity.ensure_checked()

        else:
            view = navigate_to(self, 'Details')

        view.toolbar.configuration.item_select(self.refresh_text, handle_alert=True)
        self.wait_for_relationship_refresh(wait, delay, refresh_delta)

    def wait_for_relationship_refresh(self, wait=600, delay=1, refresh_delta=10):
        logger.info('Waiting for relationship refresh')
        if wait:
            wait_for(self.is_refreshed, func_kwargs={'refresh_delta': refresh_delta}, timeout=wait,
                     delay=delay)
        elif delay != 1 or refresh_delta != 10:
            logger.info("Ignoring delay/refresh_delta parameter, because wait is set to 0")

    @variable(alias='rest')
    def last_refresh_date(self):
        try:
            name = self.ui_name if self.category == "config_manager" else self.name
            col = self.appliance.rest_api.collections.providers.find_by(name=name)[0]
            return col.last_refresh_date
        except AttributeError:
            return None

    @variable(alias='rest')
    def last_refresh_error(self):
        try:
            name = self.ui_name if self.category == "config_manager" else self.name
            col = self.appliance.rest_api.collections.providers.find_by(name=name)[0]
            return col.last_refresh_error
        except AttributeError:
            return None

    def _num_db_generic(self, table_str):
        """ Fetch number of rows related to this provider in a given table

        Args:
            table_str: Name of the table; e.g. 'vms' or 'hosts'
        """
        res = self.appliance.db.client.engine.execute(
            "SELECT count(*) "
            "FROM ext_management_systems, {0} "
            "WHERE {0}.ems_id=ext_management_systems.id "
            "AND ext_management_systems.name='{1}'".format(table_str, self.name))
        return int(res.first()[0])

    def _do_stats_match(self, client, stats_to_match=None, refresh_timer=None, ui=False):
        """ A private function to match a set of statistics, with a Provider.

        This function checks if the list of stats match, if not, the page is refreshed.

        Note: Provider mgmt_system uses the same key names as this Provider class to avoid
            having to map keyname/attributes e.g. ``num_template``, ``num_vm``.

        Args:
            client: A provider mgmt_system instance.
            stats_to_match: A list of key/attribute names to match.

        Raises:
            KeyError: If the host stats does not contain the specified key.
            ProviderHasNoProperty: If the provider does not have the property defined.
        """
        host_stats = client.stats(*stats_to_match)
        method = None
        if ui:
            self.browser.selenium.refresh()
            method = 'ui'

        if refresh_timer:
            if refresh_timer.is_it_time():
                logger.info(' Time for a refresh!')
                self.refresh_provider_relationships()
                refresh_timer.reset()

        for stat in stats_to_match:
            try:
                cfme_stat = getattr(self, stat)(method=method)
                success, value = tol_check(host_stats[stat],
                                           cfme_stat,
                                           min_error=0.05,
                                           low_val_correction=2)
                logger.info(' Matching stat [%s], Host(%s), CFME(%s), '
                    'with tolerance %s is %s', stat, host_stats[stat], cfme_stat, value, success)
                if not success:
                    return False
            except KeyError:
                raise HostStatsNotContains(
                    f"Host stats information does not contain '{stat}'")
            except AttributeError:
                raise ProviderHasNoProperty(f"Provider does not know how to get '{stat}'")
        else:
            return True

    @property
    def exists(self):
        """ Returns ``True`` if a provider of the same name exists on the appliance
        """
        if self.name in self.appliance.managed_provider_names:
            return True
        return False

    def wait_for_delete(self):
        logger.info('Waiting for a provider to delete...')
        self.rest_api_entity.wait_not_exists(message="Wait provider to disappear", num_sec=1000)

    def load_details(self, refresh=False):
        """To be compatible with the Taggable and PolicyProfileAssignable mixins.

        Returns: ProviderDetails view
        """
        view = navigate_to(self, 'Details')
        if refresh:
            view.toolbar.reload.click()
        return view

    @classmethod
    def get_credentials(cls, credential_dict, cred_type=None):
        """Processes a credential dictionary into a credential object.

        Args:
            credential_dict: A credential dictionary.
            cred_type: Type of credential (None, token, ssh, amqp, ...)

        Returns:
            A :py:class:`cfme.base.credential.Credential` instance.
        """
        domain = credential_dict.get('domain')
        token = credential_dict.get('token')
        if not cred_type:
            return Credential(principal=credential_dict['username'],
                              secret=credential_dict['password'],
                              domain=domain)
        elif cred_type == 'amqp':
            return EventsCredential(principal=credential_dict['username'],
                                    secret=credential_dict['password'])

        elif cred_type == 'ssh':
            return SSHCredential(principal=credential_dict['username'],
                                 secret=credential_dict['password'])
        elif cred_type == 'candu':
            return CANDUCredential(principal=credential_dict['username'],
                                   secret=credential_dict['password'])
        elif cred_type == 'token':
            return TokenCredential(token=token)

    @classmethod
    def get_credentials_from_config(cls, credential_config_name, cred_type=None):
        """Retrieves the credential by its name from the credentials yaml.

        Args:
            credential_config_name: The name of the credential in the credentials yaml.
            cred_type: Type of credential (None, token, ssh, amqp, ...)

        Returns:
            A :py:class:`cfme.base.credential.Credential` instance.
        """
        creds = conf.credentials[credential_config_name]
        return cls.get_credentials(creds, cred_type=cred_type)

    @classmethod
    def process_credential_yaml_key(cls, cred_yaml_key, cred_type=None):
        """Function that detects if it needs to look up credentials in the credential yaml and acts
        as expected.

        If you pass a dictionary, it assumes it does not need to look up in the credentials yaml
        file.
        If anything else is passed, it continues with looking up the credentials in the yaml file.

        Args:
            cred_yaml_key: Either a string pointing to the credentials.yaml or a dictionary which is
                considered as the credentials.

        Returns:
            :py:class:`cfme.base.credential.Credential` instance
        """
        if isinstance(cred_yaml_key, dict):
            return cls.get_credentials(cred_yaml_key, cred_type=cred_type)
        else:
            return cls.get_credentials_from_config(cred_yaml_key, cred_type=cred_type)

    # Move to collection
    @classmethod
    def clear_providers(cls):
        """ Clear all providers of given class on the appliance """
        from cfme.utils.appliance import current_appliance as app
        # Delete all matching
        for prov in app.managed_known_providers:
            if prov.one_of(cls):
                logger.info('Deleting provider: %s', prov.name)
                prov.delete_rest()
        # Wait for all matching to be deleted
        for prov in app.managed_known_providers:
            if prov.one_of(cls):
                prov.wait_for_delete()

    def one_of(self, *classes):
        """ Returns true if provider is an instance of any of the classes or sublasses there of"""
        return isinstance(self, classes)

    # These methods need to be overridden in the provider specific classes
    def get_console_connection_status(self):
        raise NotImplementedError("This method is not implemented for given provider")

    def get_remote_console_canvas(self):
        raise NotImplementedError("This method is not implemented for given provider")

    def get_console_ctrl_alt_del_btn(self):
        raise NotImplementedError("This method is not implemented for given provider")

    def get_console_fullscreen_btn(self):
        raise NotImplementedError("This method is not implemented for given provider")

    def get_console_type_name(self):
        raise NotImplementedError("This method is not implemented for given provider")

    def get_all_provider_ids(self):
        """
        Returns an integer list of provider ID's via the REST API
        """
        # TODO: Move to ProviderCollection
        logger.debug('Retrieving the list of provider ids')

        provider_ids = []
        try:
            for prov in self.appliance.rest_api.collections.providers.all:
                provider_ids.append(prov.id)
        except APIException:
            return None

        return provider_ids

    def get_all_vm_ids(self):
        """
        Returns an integer list of vm ID's via the REST API
        """
        # TODO: Move to VMCollection or BaseVMCollection
        logger.debug('Retrieving the list of vm ids')

        vm_ids = []
        try:
            for vm in self.appliance.rest_api.collections.vms.all:
                vm_ids.append(vm.id)
        except APIException:
            return None

        return vm_ids

    def get_all_host_ids(self):
        """
        Returns an integer list of host ID's via the Rest API
        """
        # TODO: Move to HostCollection
        logger.debug('Retrieving the list of host ids')

        host_ids = []
        try:
            for host in self.appliance.rest_api.collections.hosts.all:
                host_ids.append(host.id)
        except APIException:
            return None
        return host_ids

    def get_all_template_ids(self):
        """Returns an integer list of template ID's via the Rest API"""
        # TODO: Move to TemplateCollection
        logger.debug('Retrieving the list of template ids')

        template_ids = []
        try:
            for template in self.appliance.rest_api.collections.templates.all:
                template_ids.append(template.id)
        except APIException:
            return None
        return template_ids

    def get_provider_details(self, provider_id):
        """Returns the name, and type associated with the provider_id"""
        # TODO: Move to ProviderCollection.find
        logger.debug(f'Retrieving the provider details for ID: {provider_id}')

        details = {}
        try:
            prov = self.appliance.rest_api.collections.providers.get(id=provider_id)
        except APIException:
            return None
        details['id'] = prov.id
        details['name'] = prov.name
        details['type'] = prov.type

        return details

    def get_vm_details(self, vm_id):
        """
        Returns the name, type, vendor, host_id, and power_state associated with
        the vm_id.
        """
        # TODO: Move to VMCollection.find
        logger.debug(f'Retrieving the VM details for ID: {vm_id}')

        details = {}
        try:
            vm = self.appliance.rest_api.collections.vms.get(id=vm_id)
        except APIException:
            return None

        details['id'] = vm.id
        details['ems_id'] = vm.ems_id
        details['name'] = vm.name
        details['type'] = vm.type
        details['vendor'] = vm.vendor
        details['host_id'] = vm.host_id
        details['power_state'] = vm.power_state
        return details

    def get_template_details(self, template_id):
        """
        Returns the name, type, and guid associated with the template_id
        """
        # TODO: Move to TemplateCollection.find
        logger.debug('Retrieving the template details for ID: {}'
                     .format(template_id))

        template_details = {}
        try:
            template = self.appliance.rest_api.collections.templates.get(id=template_id)
        except APIException:
            return None

        template_details['name'] = template.name
        template_details['type'] = template.type
        template_details['guid'] = template.guid
        return template_details

    def get_all_template_details(self):
        """
        Returns a dictionary mapping template ids to their name, type, and guid
        """
        # TODO: Move to TemplateCollection.all
        all_details = {}
        for id in self.get_all_template_ids():
            all_details[id] = self.get_template_details(id)
        return all_details

    def get_vm_id(self, vm_name):
        """
        Return the ID associated with the specified VM name
        """
        # TODO: Get Provider object from VMCollection.find, then use VM.id to get the id
        logger.debug(f'Retrieving the ID for VM: {vm_name}')
        for vm_id in self.get_all_vm_ids():
            details = self.get_vm_details(vm_id)
            if details['name'] == vm_name:
                return vm_id

    def get_vm_ids(self, vm_names):
        """
        Returns a dictionary mapping each VM name to it's id
        """
        # TODO: Move to VMCollection.find or VMCollection.all
        name_list = vm_names[:]
        logger.debug('Retrieving the IDs for {} VM(s)'.format(len(name_list)))
        id_map = {}
        for vm_id in self.get_all_vm_ids():
            if not name_list:
                break
            vm_name = self.get_vm_details(vm_id)['name']
            if vm_name in name_list:
                id_map[vm_name] = vm_id
                name_list.remove(vm_name)
        return id_map

    def get_template_guids(self, template_dict):
        """
        Returns a list of tuples. The inner tuples are formated so that each guid
        is in index 0, and its provider's name is in index 1. Expects a dictionary
        mapping a provider to its templates
        """
        # TODO: Move to TemplateCollection
        result_list = []
        all_template_details = self.get_all_template_details()
        for provider, templates in template_dict.items():
            for template_name in templates:
                inner_tuple = ()
                for id in all_template_details:
                    if ((all_template_details[id]['name'] == template_name) and
                            (self.db_types[0] in all_template_details[id]['type'])):
                        inner_tuple += (all_template_details[id]['guid'],)
                        inner_tuple += (provider,)
                        result_list.append(inner_tuple)
        return result_list


class CloudInfraProviderMixin:
    detail_page_suffix = 'provider'
    edit_page_suffix = 'provider_edit'
    refresh_text = "Refresh Relationships and Power States"

    @property
    def hostname(self):
        return getattr(self.default_endpoint, "hostname", None)

    @hostname.setter
    def hostname(self, value):
        if self.default_endpoint:
            if value:
                self.default_endpoint.hostname = value
        else:
            logger.warning("can't set hostname because default endpoint is absent")

    @property
    def ip_address(self):
        return getattr(self.default_endpoint, "ipaddress", resolve_hostname(str(self.hostname)))

    @ip_address.setter
    def ip_address(self, value):
        if self.default_endpoint:
            if value:
                self.default_endpoint.ipaddress = value
        else:
            logger.warning("can't set ipaddress because default endpoint is absent")

    @variable(alias="db")
    def num_template(self):
        """ Returns the providers number of templates, as shown on the Details page."""
        ext_management_systems = self.appliance.db.client["ext_management_systems"]
        vms = self.appliance.db.client["vms"]
        temlist = list(self.appliance.db.client.session.query(vms.name)
                       .join(ext_management_systems, vms.ems_id == ext_management_systems.id)
                       .filter(ext_management_systems.name == self.name)
                       .filter(vms.template == True))  # NOQA
        return len(temlist)

    @num_template.variant('ui')
    def num_template_ui(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of(self.template_name))

    @variable(alias="db")
    def num_vm(self):
        """ Returns the providers number of instances, as shown on the Details page."""
        ext_management_systems = self.appliance.db.client["ext_management_systems"]
        vms = self.appliance.db.client["vms"]
        vmlist = list(self.appliance.db.client.session.query(vms.name)
                      .join(ext_management_systems, vms.ems_id == ext_management_systems.id)
                      .filter(ext_management_systems.name == self.name)
                      .filter(vms.template == False))  # NOQA
        return len(vmlist)

    @num_vm.variant('ui')
    def num_vm_ui(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of(self.vm_name))

    def load_all_provider_instances(self):
        return self.load_all_provider_vms()

    def load_all_provider_vms(self):
        """ Loads the list of instances that are running under the provider.

        """
        view = navigate_to(self, 'Details')
        if view.entities.summary("Relationships").get_text_of(self.vm_name) == "0":
            return False
        else:
            view.entities.summary("Relationships").click_at(self.vm_name)
            return True

    def load_all_provider_images(self):
        self.load_all_provider_templates()

    def load_all_provider_templates(self):
        """ Loads the list of images that are available under the provider.

        """
        # todo: replace these methods with new nav location
        view = navigate_to(self, 'Details')
        if view.entities.summary("Relationships").get_text_of(self.template_name) == "0":
            return False
        else:
            view.entities.summary("Relationships").click_at(self.template_name)
            return True


class DefaultEndpoint:
    credential_class = Credential
    name = 'default'

    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            if key == 'credentials' and isinstance(val, str):
                val = self.credential_class.from_config(val)
            elif key == 'credentials' and isinstance(val, Iterable):
                val = self.credential_class.from_plaintext(val)
            elif key == 'credentials' and isinstance(val, (Credential, TokenCredential)):
                pass
            setattr(self, key, val)

    @property
    def view_value_mapping(self):
        return {'hostname': getattr(self, 'hostname', None)}


class CANDUEndpoint(DefaultEndpoint):
    credential_class = CANDUCredential
    name = 'candu'

    @property
    def view_value_mapping(self):
        return {'hostname': getattr(self, 'hostname', None),
                'api_port': getattr(self, 'api_port', None),
                'database_name': getattr(self, 'database', None)}


class SmartStateDockerEndpoint(DefaultEndpoint):
    credential_class = Credential
    name = 'smartstate'

    @property
    def view_value_mapping(self):
        return {}


class EventsEndpoint(DefaultEndpoint):
    credential_class = EventsCredential
    name = 'events'

    @property
    def view_value_mapping(self):
        return {'event_stream': getattr(self, 'event_stream', None),
                'security_protocol': getattr(self, 'security_protocol', None),
                'hostname': getattr(self, 'hostname', None),
                'api_port': getattr(self, 'api_port', None)}


class SSHEndpoint(DefaultEndpoint):
    credential_class = SSHCredential
    name = 'rsa_keypair'

    @property
    def view_value_mapping(self):
        return {}


class VMRCEndpoint(DefaultEndpoint):
    credential_class = Credential
    name = 'vmrc'

    @property
    def view_value_mapping(self):
        return {}


class DefaultEndpointForm(View):
    hostname = Input('default_hostname')
    username = Input('default_userid')
    password = Input('default_password')
    confirm_password = Input('default_verify')
    change_password = Text(locator='.//a[normalize-space(.)="Change stored password"]')

    validate = Button('Validate')


@navigator.register(BaseProvider, 'DatastoresOfProvider')
class DatastoresOfProvider(CFMENavigateStep):
    VIEW = ProviderAllDatastoresView

    def prerequisite(self):
        return navigate_to(self.obj, 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.summary('Relationships').click_at('Datastores')
