import datetime
from collections import Iterable

from manageiq_client.api import APIException
from widgetastic.widget import View, Text
from widgetastic_patternfly import Input, Button

from cfme.base.credential import (
    Credential, EventsCredential, TokenCredential, SSHCredential, CANDUCredential)
from cfme.common import WidgetasticTaggable
from cfme.exceptions import (
    ProviderHasNoKey, HostStatsNotContains, ProviderHasNoProperty, ItemNotFound)
from cfme.utils import ParamClassName, version, conf
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigate_to, navigator
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.net import resolve_hostname
from cfme.utils.stats import tol_check
from cfme.utils.update import Updateable
from cfme.utils.varmeth import variable
from cfme.utils.wait import wait_for, RefreshTimer
from . import PolicyProfileAssignable, Taggable, SummaryMixin


def base_types():
    from pkg_resources import iter_entry_points
    return {ep.name: ep.resolve() for ep in iter_entry_points('manageiq.provider_categories')}


def provider_types(category):
    from pkg_resources import iter_entry_points
    return {
        ep.name: ep.resolve() for ep in iter_entry_points(
            'manageiq.provider_types.{}'.format(category))
    }


def all_types():
    all_types = base_types()
    for category in all_types.keys():
        all_types.update(provider_types(category))
    return all_types


class BaseProvider(Taggable, Updateable, SummaryMixin, Navigatable):
    # List of constants that every non-abstract subclass must have defined
    _param_name = ParamClassName('name')
    STATS_TO_MATCH = []
    db_types = ["Providers"]

    def __hash__(self):
        return hash(self.key) ^ hash(type(self))

    def __eq__(self, other):
        return type(self) is type(other) and self.key == other.key

    @property
    def data(self):
        return self.get_yaml_data()

    @property
    def mgmt(self):
        return self.get_mgmt_system()

    @property
    def type(self):
        return self.type_name

    @property
    def id(self):
        """"
        Return the ID associated with the specified provider name
        """
        return self.appliance.rest_api.collections.providers.find_by(name=self.name)[0].id

    @property
    def version(self):
        return self.data['version']

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines and usually overidden"""
        return {}

    @property
    def default_endpoint(self):
        return self.endpoints.get('default') if hasattr(self, 'endpoints') else None

    def get_yaml_data(self):
        """ Returns yaml data for this provider.
        """
        if hasattr(self, 'provider_data') and self.provider_data is not None:
            return self.provider_data
        elif self.key is not None:
            return conf.cfme_data['management_systems'][self.key]
        else:
            raise ProviderHasNoKey(
                'Provider {} has no key, so cannot get yaml data'.format(self.name))

    def get_mgmt_system(self):
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
                'Provider {} has no key, so cannot get mgmt system'.format(self.name))

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
                (default: ``True``)

        Returns:
            True if it was created, False if it already existed
        """
        if check_existing and self.exists:
            created = False
        else:
            created = True

            logger.info('Setting up Infra Provider: %s', self.key)
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
                cancel_text = ('Add of {} Provider was '
                               'cancelled by the user'.format(self.string_name))

                main_view.entities.flash.assert_message(cancel_text)
                main_view.entities.flash.assert_no_error()
            else:
                add_view.add.click()
                if main_view.is_displayed:
                    success_text = '{} Providers "{}" was saved'.format(self.string_name,
                                                                        self.name)
                    main_view.entities.flash.assert_message(success_text)
                else:
                    add_view.flash.assert_no_error()
                    raise AssertionError("Provider wasn't added. It seems form isn't accurately"
                                         " filled")

        if validate_inventory:
            self.validate()

        return created

    def create_rest(self):

        logger.info('Setting up provider: %s via rest', self.key)
        try:
            self.appliance.rest_api.collections.providers.action.create(
                hostname=self.hostname,
                ipaddress=self.ip_address,
                name=self.name,
                type="ManageIQ::Providers::{}".format(self.db_types[0]),
                credentials={'userid': self.endpoints['default'].credentials.principal,
                             'password': self.endpoints['default'].credentials.secret})

            return self.appliance.rest_api.response.status_code == 200
        except APIException:
            return None

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
            endpoints = self._prepare_endpoints(endpoints)

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
            main_view.entities.flash.assert_message(cancel_text)
            main_view.entities.flash.assert_no_error()
        else:
            edit_view.save.click()
            if endpoints:
                for endp_name, endp in endpoints.items():
                    self.endpoints[endp_name] = endp
            if updates:
                self.name = updates.get('name', self.name)

            if BZ.bugzilla.get_bug(1436341).is_opened and version.current_version() > '5.8':
                logger.warning('Skipping flash message verification because of BZ 1436341')
                return

            success_text = '{} Provider "{}" was saved'.format(self.string_name, self.name)
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

    def delete(self, cancel=True):
        """
        Deletes a provider from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """
        view = navigate_to(self, 'Details')
        item_title = version.pick({'5.9': 'Remove this {} Provider from Inventory',
                                   version.LOWEST: 'Remove this {} Provider'})
        view.toolbar.configuration.item_select(item_title.format(self.string_name),
                                               handle_alert=not cancel)
        if not cancel:
            msg = ('Delete initiated for 1 {} Provider from '
                   'the {} Database'.format(self.string_name, self.appliance.product_name))
            view.flash.assert_success_message(msg)

    def setup(self, rest=False):
        """
        Sets up the provider robustly
        """
        return self.create(
            cancel=False, validate_credentials=True, check_existing=True, validate_inventory=True)

    def delete_if_exists(self, *args, **kwargs):
        """Combines ``.exists`` and ``.delete()`` as a shortcut for ``request.addfinalizer``

        Returns: True if provider existed and delete was initiated, False otherwise
        """
        if self.exists:
            self.delete(*args, **kwargs)
            return True
        return False

    @variable(alias='rest')
    def is_refreshed(self, refresh_timer=None, refresh_delta=600):
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
            self.refresh_provider_relationships()
            return False
        else:
            return True

    def validate(self):
        refresh_timer = RefreshTimer(time_for_refresh=300)
        try:
            wait_for(self.is_refreshed,
                     [refresh_timer],
                     message="is_refreshed",
                     num_sec=1000,
                     delay=60,
                     handle_exception=True)
        except Exception:
            # To see the possible error.
            self.load_details(refresh=True)
            raise

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
    def refresh_provider_relationships(self, from_list_view=False):
        # from_list_view is ignored as it is included here for sake of compatibility with UI call.
        logger.debug('Refreshing provider relationships')
        col = self.appliance.rest_api.collections.providers.find_by(name=self.name)
        try:
            col[0].action.refresh()
        except IndexError:
            raise Exception("Provider collection empty")

    @refresh_provider_relationships.variant('ui')
    def refresh_provider_relationships_ui(self, from_list_view=False):
        """Clicks on Refresh relationships button in provider"""
        if from_list_view:
            view = navigate_to(self, 'All')
            entity = view.entities.get_entity(self.name, surf_pages=True)
            entity.check()

        else:
            view = navigate_to(self, 'Details')

        view.toolbar.configuration.item_select(self.refresh_text, handle_alert=True)

    @variable(alias='rest')
    def last_refresh_date(self):
        try:
            col = self.appliance.rest_api.collections.providers.find_by(name=self.name)[0]
            return col.last_refresh_date
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
                    "Host stats information does not contain '{}'".format(stat))
            except AttributeError:
                raise ProviderHasNoProperty("Provider does not know how to get '{}'".format(stat))
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
        view = navigate_to(self, 'All')

        def is_entity_present():
            try:
                view.entities.get_entity(self.name, surf_pages=True)
                return True
            except ItemNotFound:
                return False

        logger.info('Waiting for a provider to delete...')
        wait_for(is_entity_present, fail_condition=True,
                 message="Wait provider to disappear", num_sec=1000,
                 fail_func=self.browser.selenium.refresh)

    def load_details(self, refresh=False):
        """To be compatible with the Taggable and PolicyProfileAssignable mixins.

        Returns: ProviderDetails view
        """
        view = navigate_to(self, 'Details')
        if refresh:
            view.toolbar.reload.click()
        return view

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific provider.

        Args:
            *ident: An SummaryTable title, followed by the Key name, e.g. "Relationships", "Images"


        Returns: A string representing the contents of passed field value.
        """
        view = self.load_details()
        block, field = ident
        return getattr(view.entities, block.lower()).get_text_of(field)

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
        app.rest_api.collections.providers.reload()
        for prov in app.rest_api.collections.providers.all:
            try:
                if any([True for db_type in cls.db_types if db_type in prov.type]):
                    logger.info('Deleting provider: %s', prov.name)
                    prov.action.delete()
                    prov.wait_not_exists()
            except APIException as ex:
                # Provider is already gone (usually caused by NetworkManager objs)
                if 'RecordNotFound' not in str(ex):
                    raise ex
        app.rest_api.collections.providers.reload()

    def one_of(self, *classes):
        """ Returns true if provider is an instance of any of the classes or sublasses there of"""
        return isinstance(self, classes)

    @staticmethod
    def _prepare_endpoints(endpoints):
        if not endpoints:
            return {}
        elif isinstance(endpoints, dict):
            return endpoints
        elif isinstance(endpoints, Iterable):
            return {(e.name, e) for e in endpoints}
        elif isinstance(endpoints, DefaultEndpoint):
            return {endpoints.name: endpoints}
        else:
            raise ValueError("Endpoints should be either dict or endpoint class")

    # These methods need to be overridden in the provider specific classes
    def get_console_connection_status(self):
        raise NotImplementedError("This method is not implemented for given provider")

    def get_remote_console_canvas(self):
        raise NotImplementedError("This method is not implemented for given provider")

    def get_console_ctrl_alt_del_btn(self):
        raise NotImplementedError("This method is not implemented for given provider")

    def get_console_fullscreen_btn(self):
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
        logger.debug('Retrieving the provider details for ID: {}'.format(provider_id))

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
        logger.debug('Retrieving the VM details for ID: {}'.format(vm_id))

        details = {}
        try:
            vm = self.appliance.rest_api.collections.vms.get(id=vm_id)
        except APIException:
            return None

        details['id'] = vm.id
        details['ems_id'] = vm.ems_id
        details['name'] = vm.name
        details['type'] = vm.type
        details['vendor'] = vm.vendore
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
        logger.debug('Retrieving the ID for VM: {}'.format(vm_name))
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
        for provider, templates in template_dict.iteritems():
            for template_name in templates:
                inner_tuple = ()
                for id in all_template_details:
                    if ((all_template_details[id]['name'] == template_name) and
                            (self.db_types[0] in all_template_details[id]['type'])):
                        inner_tuple += (all_template_details[id]['guid'],)
                        inner_tuple += (provider,)
                        result_list.append(inner_tuple)
        return result_list


class CloudInfraProvider(BaseProvider, PolicyProfileAssignable, WidgetasticTaggable):
    vm_name = ""
    template_name = ""
    detail_page_suffix = 'provider'
    edit_page_suffix = 'provider_edit'
    refresh_text = "Refresh Relationships and Power States"
    db_types = ["CloudManager", "InfraManager"]

    @property
    def hostname(self):
        return getattr(self.default_endpoint, "hostname", None)

    @hostname.setter
    def hostname(self, value):
        if self.default_endpoint:
            if value:
                self.default_endpoint.hostname = value
        else:
            logger.warn("can't set hostname because default endpoint is absent")

    @property
    def ip_address(self):
        return getattr(self.default_endpoint, "ipaddress", resolve_hostname(str(self.hostname)))

    @ip_address.setter
    def ip_address(self, value):
        if self.default_endpoint:
            if value:
                self.default_endpoint.ipaddress = value
        else:
            logger.warn("can't set ipaddress because default endpoint is absent")

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
        return int(self.get_detail("Relationships", self.template_name))

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
        return int(self.get_detail("Relationships", self.vm_name))

    def load_all_provider_instances(self):
        return self.load_all_provider_vms()

    def load_all_provider_vms(self):
        """ Loads the list of instances that are running under the provider.

        """
        view = navigate_to(self, 'Details')
        if view.entities.relationships.get_text_of(self.vm_name) == "0":
            return False
        else:
            view.entities.relationships.click_at(self.vm_name)
            return True

    def load_all_provider_images(self):
        self.load_all_provider_templates()

    def load_all_provider_templates(self):
        """ Loads the list of images that are available under the provider.

        """
        # todo: replace these methods with new nav location
        view = navigate_to(self, 'Details')
        if view.entities.relationships.get_text_of(self.template_name) == "0":
            return False
        else:
            view.entities.relationships.click_at(self.template_name)
            return True


def cleanup_vm(vm_name, provider):
    try:
        logger.info('Cleaning up VM %s on provider %s', vm_name, provider.key)
        provider.mgmt.delete_vm(vm_name)
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s', vm_name, provider.key)


class DefaultEndpoint(object):
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
        return {'hostname': self.hostname}


class CANDUEndpoint(DefaultEndpoint):
    credential_class = CANDUCredential
    name = 'candu'

    @property
    def view_value_mapping(self):
        return {'hostname': self.hostname,
                'api_port': getattr(self, 'api_port', None),
                'database_name': self.database}


class EventsEndpoint(DefaultEndpoint):
    credential_class = EventsCredential
    name = 'events'

    @property
    def view_value_mapping(self):
        return {'event_stream': self.event_stream,
                'security_protocol': getattr(self, 'security_protocol', None),
                'hostname': self.hostname,
                'api_port': getattr(self, 'api_port', None),
                }


class SSHEndpoint(DefaultEndpoint):
    credential_class = SSHCredential
    name = 'rsa_keypair'

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
