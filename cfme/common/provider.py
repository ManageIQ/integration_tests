import datetime
from functools import partial

from manageiq_client.api import APIException

from cfme.base.credential import Credential, EventsCredential, TokenCredential, SSHCredential, \
    CANDUCredential, AzureCredential, ServiceAccountCredential
import cfme.fixtures.pytest_selenium as sel
from cfme.exceptions import (
    ProviderHasNoKey, HostStatsNotContains, ProviderHasNoProperty,
    FlashMessageException)
from cfme.web_ui import breadcrumbs_names, summary_title
from cfme.web_ui import flash, Quadicon, CheckboxTree, Region, fill, Form
from cfme.web_ui import form_buttons, paginator
from utils import ParamClassName, version
from cfme.web_ui import toolbar as tb
from utils import conf
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigate_to
from utils.blockers import BZ
from utils.browser import ensure_browser_open
from utils.log import logger
from utils.stats import tol_check
from utils.update import Updateable
from utils.varmeth import variable
from utils.wait import wait_for, RefreshTimer
from . import PolicyProfileAssignable, Taggable, SummaryMixin

cfg_btn = partial(tb.select, 'Configuration')

manage_policies_tree = CheckboxTree("//div[@id='protect_treebox']/ul")

details_page = Region(infoblock_type='detail')


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
    string_name = ""
    page_name = ""
    edit_page_suffix = ""
    detail_page_suffix = ""
    refresh_text = ""
    quad_name = None
    _properties_form = None
    _properties_region = None
    add_provider_button = None
    save_button = None
    db_types = ["Providers"]

    def __hash__(self):
        return hash(self.key) ^ hash(type(self))

    def __eq__(self, other):
        return type(self) is type(other) and self.key == other.key

    @property
    def properties_form(self):
        if self._properties_region:
            return self._properties_region.properties_form
        else:
            return self._properties_form

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
    def version(self):
        return self.data['version']

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines and usually overidden"""
        return {}

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
        from utils.providers import get_mgmt

        if self.key:
            return get_mgmt(self.key)
        elif getattr(self, 'provider_data', None):
            return get_mgmt(self.provider_data)
        else:
            raise ProviderHasNoKey(
                'Provider {} has no key, so cannot get mgmt system'.format(self.name))

    def _submit(self, cancel, submit_button):
        if cancel:
            form_buttons.cancel()
            # sel.wait_for_element(page.configuration_btn)
        else:
            submit_button()
            flash.assert_no_errors()

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
            logger.info('Setting up provider: %s', self.key)
            navigate_to(self, 'Add')
            fill(self.properties_form, self._form_mapping(True, hawkular=False, **self.__dict__))
            for cred in self.credentials:
                fill(self.credentials[cred].form, self.credentials[cred],
                     validate=validate_credentials)
            self._submit(cancel, self.add_provider_button)
            if not cancel:
                flash.assert_message_match('{} Providers "{}" was saved'.format(self.string_name,
                                                                                self.name))
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
        """
        navigate_to(self, 'Edit')
        fill(self.properties_form, self._form_mapping(**updates))
        for cred in self.credentials:
            fill(self.credentials[cred].form, updates.get('credentials', {}).get(cred, None),
                 validate=validate_credentials)
        self._submit(cancel, self.save_button)
        name = updates.get('name', self.name)
        if not cancel:
            if BZ.bugzilla.get_bug(1436341).is_opened and version.current_version() > '5.8':
                logger.warning('Skipping flash message verification because of BZ 1436341')
                return
            flash.assert_message_match(
                '{} Provider "{}" was saved'.format(self.string_name, name))

    def delete(self, cancel=True):
        """
        Deletes a provider from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """
        self.load_details()
        cfg_btn('Remove this {} Provider'.format(self.string_name),
            invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        if not cancel:
            flash.assert_message_match(
                'Delete initiated for 1 {} Provider from the {} Database'.format(
                    self.string_name, self.appliance.product_name))

    def setup(self):
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
    def is_refreshed(self, refresh_timer=None):
        if refresh_timer:
            if refresh_timer.is_it_time():
                logger.info(' Time for a refresh!')
                self.refresh_provider_relationships()
                refresh_timer.reset()
        rdate = self.last_refresh_date()
        if not rdate:
            return False
        td = self.appliance.utc_time() - rdate
        if td > datetime.timedelta(0, 600):
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
            navigate_to(self, 'All')
            sel.check(Quadicon(self.name, self.quad_name).checkbox())
        else:
            navigate_to(self, 'Details')
        tb.select("Configuration", self.refresh_text, invokes_alert=True)
        sel.handle_alert(cancel=False)

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
        res = self.appliance.db.engine.execute(
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
            sel.refresh()
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
        navigate_to(self, 'All')
        quad = Quadicon(self.name, self.quad_name)
        logger.info('Waiting for a provider to delete...')
        wait_for(lambda prov: not sel.is_displayed(prov), func_args=[quad], fail_condition=False,
                 message="Wait provider to disappear", num_sec=1000, fail_func=sel.refresh)

    def _on_detail_page(self):
        """ Returns ``True`` if on the providers detail page, ``False`` if not."""
        if not self.string_name:
            # No point in doing that since it is probably being called from badly configured class
            # And since it is badly configured, let's notify the user.
            logger.warning(
                'Hey, _on_details_page called from {} class which does not have string_name set'
                .format(type(self).__name__))
            return False
        ensure_browser_open()
        collection = '{} Providers'.format(self.string_name)
        title = '{} (Summary)'.format(self.name)
        return breadcrumbs_names() == [collection, title] and summary_title() == title

    def load_details(self, refresh=False):
        """To be compatible with the Taggable and PolicyProfileAssignable mixins."""
        navigate_to(self, 'Details')
        if refresh:
            tb.refresh()

    def get_detail(self, *ident, **kwargs):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific provider.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"

        Keywords:
            use_icon: Whether to use icon matching

        Returns: A string representing the contents of the InfoBlock's value.
        """
        self.load_details()
        if kwargs.get("use_icon", False):
            title, icon = ident
            return details_page.infoblock(title).by_member_icon(icon).text
        else:
            return details_page.infoblock.text(*ident)

    @classmethod
    def get_credentials(cls, credential_dict, cred_type=None):
        """Processes a credential dictionary into a credential object.

        Args:
            credential_dict: A credential dictionary.
            cred_type: Type of credential (None, token, ssh, amqp, ...)

        Returns:
            A :py:class:`cfme.base.credential.Credential` instance.
        """
        domain = credential_dict.get('domain', None)
        token = credential_dict.get('token', None)
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
        from utils.appliance import current_appliance as app
        app.rest_api.collections.providers.reload()
        logger.info('appliance ip: %s', str(app.address))
        for prov in app.rest_api.collections.providers.all:
            try:
                if any([True for db_type in cls.db_types if db_type in prov.type]):
                    logger.info('Deleting provider: %s', prov.name)
                    logger.info('Provider data: %s', str(prov.data))
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


def get_paginator_value():
    return paginator.rec_total()


class CloudInfraProvider(BaseProvider, PolicyProfileAssignable):
    vm_name = ""
    template_name = ""
    detail_page_suffix = 'provider'
    edit_page_suffix = 'provider_edit'
    refresh_text = "Refresh Relationships and Power States"
    db_types = ["CloudManager", "InfraManager"]

    def wait_for_creds_ok(self):
        """Waits for provider's credentials to become O.K. (circumvents the summary rails exc.)"""
        self.refresh_provider_relationships(from_list_view=True)

        def _wait_f():
            navigate_to(self, 'All')
            q = Quadicon(self.name, self.quad_name)
            creds = q.creds
            return "checkmark" in creds

        wait_for(_wait_f, num_sec=300, delay=5, message="credentials of {} ok!".format(self.name))

    @property
    def _assigned_policy_profiles(self):
        result = set([])
        for row in self._all_available_policy_profiles:
            if self._is_policy_profile_row_checked(row):
                result.add(row.text.encode("utf-8"))
        return result

    def get_assigned_policy_profiles(self):
        """ Return a set of Policy Profiles which are available and assigned.

        Returns: :py:class:`set` of :py:class:`str` of Policy Profile names
        """
        navigate_to(self, 'ManagePolicies')
        return self._assigned_policy_profiles

    @property
    def _unassigned_policy_profiles(self):
        result = set([])
        for row in self._all_available_policy_profiles:
            if not self._is_policy_profile_row_checked(row):
                result.add(row.text.encode("utf-8"))
        return result

    def get_unassigned_policy_profiles(self):
        """ Return a set of Policy Profiles which are available but not assigned.

        Returns: :py:class:`set` of :py:class:`str` of Policy Profile names
        """
        navigate_to(self, 'ManagePolicies')
        return self._unassigned_policy_profiles

    @property
    def _all_available_policy_profiles(self):
        pp_rows_locator = "//table/tbody/tr/td[@class='standartTreeImage']"\
            "/img[contains(@src, 'policy_profile')]/../../td[@class='standartTreeRow']"
        return sel.elements(pp_rows_locator)

    def _is_policy_profile_row_checked(self, row):
        return "Check" in row.find_element_by_xpath("../td[@width='16px']/img").get_attribute("src")

    @variable(alias="db")
    def num_template(self):
        """ Returns the providers number of templates, as shown on the Details page."""
        ext_management_systems = self.appliance.db["ext_management_systems"]
        vms = self.appliance.db["vms"]
        temlist = list(self.appliance.db.session.query(vms.name)
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
        ext_management_systems = self.appliance.db["ext_management_systems"]
        vms = self.appliance.db["vms"]
        vmlist = list(self.appliance.db.session.query(vms.name)
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

        If it could click through the link in infoblock, returns ``True``. If it sees that the
        number of instances is 0, it returns ``False``.
        """
        self.load_details()
        if details_page.infoblock.text("Relationships", self.vm_name) == "0":
            return False
        else:
            sel.click(details_page.infoblock.element("Relationships", self.vm_name))
            return True

    def load_all_provider_images(self):
        self.load_all_provider_templates()

    def load_all_provider_templates(self):
        """ Loads the list of images that are available under the provider.

        If it could click through the link in infoblock, returns ``True``. If it sees that the
        number of images is 0, it returns ``False``.
        """
        self.load_details()
        if details_page.infoblock.text("Relationships", self.template_name) == "0":
            return False
        else:
            sel.click(details_page.infoblock.element("Relationships", self.template_name))
            return True


@fill.method((Form, Credential))  # default credential
@fill.method((Form, EventsCredential))
@fill.method((Form, CANDUCredential))
@fill.method((Form, AzureCredential))
@fill.method((Form, SSHCredential))
@fill.method((Form, TokenCredential))
@fill.method((Form, ServiceAccountCredential))
def _fill_credential(form, cred, validate=None):
    """How to fill in a credential. Validates the credential if that option is passed in.
    """
    if isinstance(cred, EventsCredential):
        fill(cred.form, {
            'event_selection': 'amqp',
            'amqp_principal': cred.principal,
            'amqp_secret': cred.secret,
            'amqp_verify_secret': cred.verify_secret,
            'validate_btn': validate})
    elif isinstance(cred, CANDUCredential):
        fill(cred.form, {'candu_principal': cred.principal,
            'candu_secret': cred.secret,
            'candu_verify_secret': cred.verify_secret,
            'validate_btn': validate})
        if validate:
            # Then look up to 3 times for successful validation (THIS IS MADNESS)
            exc = None
            for __ in range(3):
                try:
                    flash.assert_success()
                except FlashMessageException as e:
                    # No success message, try again
                    exc = e
                    fill(cred.form.validate_btn, validate)
                else:
                    # Success, no error
                    break
            else:
                # Just make it explode with the original exception.
                # ``exc`` must have some contents by now since at least one except had to happen.
                raise exc

    elif isinstance(cred, AzureCredential):
        fill(cred.form, {'default_username': cred.principal,
                         'default_password': cred.secret,
                         'default_verify': cred.secret})
    elif isinstance(cred, SSHCredential):
        fill(cred.form, {'ssh_user': cred.principal, 'ssh_key': cred.secret})
    elif isinstance(cred, TokenCredential):
        fill(cred.form, {
            'token_secret': cred.token,
            'token_verify_secret': cred.verify_token,
            'validate_btn': validate
        })
        if validate:
            # Validate default creds and move on to hawkular tab validation
            flash.assert_no_errors()
            fill(cred.form, {
                'hawkular_validate_btn': validate
            })
    elif isinstance(cred, ServiceAccountCredential):
        fill(cred.form, {'google_service_account': cred.service_account, 'validate_btn': validate})
    else:
        fill(cred.form, {'default_principal': cred.principal,
            'default_secret': cred.secret,
            'default_verify_secret': cred.verify_secret,
            'validate_btn': validate})
    if validate and not isinstance(cred, CANDUCredential):
        # because we already validated it for the specific case
        flash.assert_no_errors()


def cleanup_vm(vm_name, provider):
    try:
        logger.info('Cleaning up VM %s on provider %s', vm_name, provider.key)
        provider.mgmt.delete_vm(vm_name)
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s', vm_name, provider.key)
