""" A model of a Cloud Provider in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Providers pages.
:var discover_form: A :py:class:`cfme.web_ui.Form` object describing the discover form.
:var properties_form: A :py:class:`cfme.web_ui.Form` object describing the main add form.
:var default_form: A :py:class:`cfme.web_ui.Form` object describing the default credentials form.
:var amqp_form: A :py:class:`cfme.web_ui.Form` object describing the AMQP credentials form.
"""

from functools import partial

import ui_navigate as nav

import cfme
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import flash
from cfme.web_ui import form_buttons
from cfme.web_ui import toolbar as tb
import cfme.web_ui.menu  # so that menu is already loaded before grafting onto it
from cfme.exceptions import (
    HostStatsNotContains, ProviderHasNoProperty, ProviderHasNoKey, UnknownProviderType
)
from cfme.web_ui import Region, Quadicon, Form, Select, CheckboxTree, fill, paginator
from cfme.web_ui import Input
from utils import conf
from utils.db import cfmedb
from utils.log import logger
from utils.providers import provider_factory
from utils.update import Updateable
from utils.wait import wait_for, RefreshTimer
from utils import version
from utils.pretty import Pretty
from utils.signals import fire
from utils.stats import tol_check

# Specific Add button
add_provider_button = form_buttons.FormButton("Add this Cloud Provider")

# Forms
discover_form = Form(
    fields=[
        ('username', "#userid"),
        ('password', "#password"),
        ('password_verify', "#verify"),
        ('start_button', form_buttons.FormButton("Start the Host Discovery"))
    ])

properties_form = Form(
    fields=[
        ('type_select', Select("select#server_emstype")),
        ('name_text', Input("name")),
        ('hostname_text', Input("hostname")),
        ('ipaddress_text', Input("ipaddress"), {"removed_since": "5.4.0.0.15"}),
        ('amazon_region_select', Select(
            {
                version.LOWEST: "select#hostname",
                "5.3.0.14": "select#provider_region",
            }
        )),
        ('api_port', Input("port")),
    ])

credential_form = Form(
    fields=[
        ('default_button', "//div[@id='auth_tabs']/ul/li/a[@href='#default']"),
        ('default_principal', "#default_userid"),
        ('default_secret', "#default_password"),
        ('default_verify_secret', "#default_verify"),
        ('amqp_button', "//div[@id='auth_tabs']/ul/li/a[@href='#amqp']"),
        ('amqp_principal', "#amqp_userid"),
        ('amqp_secret', "#amqp_password"),
        ('amqp_verify_secret', "#amqp_verify"),
        ('validate_btn', form_buttons.validate)
    ])

manage_policies_tree = CheckboxTree(
    {
        version.LOWEST: "//div[@id='treebox']/div/table",
        "5.3": "//div[@id='protect_treebox']/ul"
    }
)

details_page = Region(infoblock_type='detail')

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')
mon_btn = partial(tb.select, 'Monitoring')

nav.add_branch('clouds_providers',
               {'clouds_provider_new': lambda _: cfg_btn('Add a New Cloud Provider'),
                'clouds_provider_discover': lambda _: cfg_btn('Discover Cloud Providers'),
                'clouds_provider': [lambda ctx: sel.click(Quadicon(ctx['provider'].name,
                                                                  'cloud_prov')),
                                   {'clouds_provider_edit':
                                    lambda _: cfg_btn('Edit this Cloud Provider'),
                                    'clouds_provider_policy_assignment':
                                    lambda _: pol_btn('Manage Policies'),
                                    'cloud_provider_timelines':
                                    lambda _: mon_btn('Timelines')}]})


class Provider(Updateable, Pretty):
    """
    Abstract model of a cloud provider in cfme. See EC2Provider or OpenStackProvider.

    Args:
        name: Name of the provider.
        details: a details record (see EC2Details, OpenStackDetails inner class).
        credentials (Credential): see Credential inner class.
        key: The CFME key of the provider in the yaml.

    Usage:

        myprov = EC2Provider(name='foo',
                             region='us-west-1',
                             credentials=Provider.Credential(principal='admin', secret='foobar'))
        myprov.create()

    """
    pretty_attrs = ['name', 'credentials', 'zone', 'key']
    STATS_TO_MATCH = ['num_template', 'num_vm']

    def __init__(self, name=None, credentials=None, zone=None, key=None):
        self.name = name
        self.credentials = credentials
        self.zone = zone
        self.key = key

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name')}

    class Credential(cfme.Credential, Updateable):
        """Provider credentials

           Args:
             **kwargs: If using amqp type credential, amqp = True"""

        def __init__(self, **kwargs):
            super(Provider.Credential, self).__init__(**kwargs)
            self.amqp = kwargs.get('amqp')

    def _submit(self, cancel, submit_button):
        if cancel:
            sel.click(form_buttons.cancel)
            # sel.wait_for_element(page.configuration_btn)
        else:
            sel.click(submit_button)
            flash.assert_no_errors()

    def create(self, cancel=False, validate_credentials=False):
        """
        Creates a provider in the UI

        Args:
           cancel (boolean): Whether to cancel out of the creation.  The cancel is done
               after all the information present in the Provider has been filled in the UI.
           validate_credentials (boolean): Whether to validate credentials - if True and the
               credentials are invalid, an error will be raised.
        """
        sel.force_navigate('clouds_provider_new')
        fill(properties_form, self._form_mapping(True, **self.__dict__))
        fill(credential_form, self.credentials, validate=validate_credentials)
        self._submit(cancel, add_provider_button)
        fire("providers_changed")
        if not cancel:
            flash.assert_message_match('Cloud Providers "%s" was saved' % self.name)

    def update(self, updates, cancel=False, validate_credentials=False):
        """
        Updates a provider in the UI.  Better to use utils.update.update context
        manager than call this directly.

        Args:
           updates (dict): fields that are changing.
           cancel (boolean): whether to cancel out of the update.
        """

        sel.force_navigate('clouds_provider_edit', context={'provider': self})
        fill(properties_form, self._form_mapping(**updates))
        fill(credential_form, updates.get('credentials', None), validate=validate_credentials)
        self._submit(cancel, form_buttons.save)
        name = updates['name'] or self.name
        if not cancel:
            flash.assert_message_match('Cloud Provider "%s" was saved' % name)

    def delete(self, cancel=True):
        """
        Deletes a provider from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        sel.force_navigate('clouds_provider', context={'provider': self})
        cfg_btn('Remove this Cloud Provider from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        fire("providers_changed")
        if not cancel:
            flash.assert_message_match(
                'Delete initiated for 1 Cloud Provider from the CFME Database')

    def delete_if_exists(self, *args, **kwargs):
        """Combines ``.exists`` and ``.delete()`` as a shortcut for ``request.addfinalizer``"""
        if self.exists:
            self.delete(*args, **kwargs)

    def validate(self, db=True):
        """ Validates that the detail page matches the Providers information.

        This method logs into the provider using the mgmt_system interface and collects
        a set of statistics to be matched against the UI. The details page is then refreshed
        continuously until the matching of all items is complete. A error will be raised
        if the match is not complete within a certain defined time period.
        """

        client = self.get_mgmt_system()

        # If we're not using db, make sure we are on the provider detail page
        if not db:
            sel.force_navigate('clouds_provider', context={'provider': self})

        # Initial bullet check
        if self._do_stats_match(client, self.STATS_TO_MATCH, db=db):
            client.disconnect()
            return
        else:
            # Set off a Refresh Relationships
            sel.force_navigate('clouds_provider', context={'provider': self})
            tb.select("Configuration", "Refresh Relationships and Power States", invokes_alert=True)
            sel.handle_alert()

            refresh_timer = RefreshTimer(time_for_refresh=300)
            wait_for(self._do_stats_match,
                     [client, self.STATS_TO_MATCH, refresh_timer],
                     {'db': db},
                     message="do_stats_match_db",
                     num_sec=1000,
                     delay=60)

        client.disconnect()

    def load_all_provider_instances(self):
        """ Loads the list of instances that are running under the provider.

        If it could click through the link in infoblock, returns ``True``. If it sees that the
        number of instances is 0, it returns ``False``.
        """
        sel.force_navigate('clouds_provider', context={'provider': self})
        if details_page.infoblock.text("Relationships", "Instances") == "0":
            return False
        else:
            sel.click(details_page.infoblock.element("Relationships", "Instances"))
            return True

    def load_all_provider_images(self):
        """ Loads the list of images that are available under the provider.

        If it could click through the link in infoblock, returns ``True``. If it sees that the
        number of images is 0, it returns ``False``.
        """
        sel.force_navigate('clouds_provider', context={'provider': self})
        if details_page.infoblock.text("Relationships", "Images") == "0":
            return False
        else:
            sel.click(details_page.infoblock.element("Relationships", "Images"))
            return True

    def refresh_provider_relationships(self):
        """Clicks on Refresh relationships button in provider"""
        sel.force_navigate('clouds_provider', context={"provider": self})
        tb.select("Configuration", "Refresh Relationships and Power States", invokes_alert=True)
        sel.handle_alert(cancel=False)

    def get_yaml_data(self):
        """ Returns yaml data for this provider.
        """
        if not self.key:
            raise ProviderHasNoKey('Provider %s has no key, so cannot get yaml data')
        else:
            return conf.cfme_data.get('management_systems', {})[self.key]

    def get_mgmt_system(self):
        """ Returns the mgmt_system using the :py:func:`utils.providers.provider_factory` method.
        """
        if not self.key:
            raise ProviderHasNoKey('Provider %s has no key, so cannot get mgmt system')
        else:
            return provider_factory(self.key)

    def _load_details(self):
        if not self._on_detail_page():
            sel.force_navigate('cloud_provider', context={'provider': self})

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific provider.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        if not self._on_detail_page():
            sel.force_navigate('clouds_provider', context={'provider': self})
        return details_page.infoblock.text(*ident)

    def _do_stats_match(self, client, stats_to_match=None, refresh_timer=None, db=True):
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
        if not db:
            sel.refresh()

        if refresh_timer:
            if refresh_timer.is_it_time():
                logger.info(' Time for a refresh!')
                sel.force_navigate('clouds_provider', context={'provider': self})
                tb.select("Configuration", "Refresh Relationships and Power States",
                          invokes_alert=True)
                sel.handle_alert(cancel=False)
                refresh_timer.reset()

        for stat in stats_to_match:
            try:
                cfme_stat = getattr(self, stat)(db=db)
                success, value = tol_check(host_stats[stat],
                                           cfme_stat,
                                           min_error=0.05,
                                           low_val_correction=2)
                logger.info(' Matching stat [{}], Host({}), CFME({}), '
                    'with tolerance {} is {}'.format(stat, host_stats[stat], cfme_stat,
                                                     value, success))
                if not success:
                    return False
            except KeyError:
                raise HostStatsNotContains("Host stats information does not contain '%s'" % stat)
            except AttributeError:
                raise ProviderHasNoProperty("Provider does not know how to get '%s'" % stat)
        else:
            return True

    def _on_detail_page(self):
        """ Returns ``True`` if on the providers detail page, ``False`` if not."""
        return sel.is_displayed('//div[@class="dhtmlxInfoBarLabel-2"][contains(., "%s")]'
                                % self.name)

    def num_template(self, db=True):
        """ Returns the providers number of templates, as shown on the Details page."""
        if db:
            ext_management_systems = cfmedb()["ext_management_systems"]
            vms = cfmedb()["vms"]
            truthy = True  # This is to prevent a lint error with ==True
            temlist = list(cfmedb().session.query(vms.name)
                           .join(ext_management_systems, vms.ems_id == ext_management_systems.id)
                           .filter(ext_management_systems.name == self.name)
                           .filter(vms.template == truthy))
            return len(temlist)
        else:
            return int(self.get_detail("Relationships", "Images"))

    def num_vm(self, db=True):
        """ Returns the providers number of instances, as shown on the Details page."""
        if db:
            ext_management_systems = cfmedb()["ext_management_systems"]
            vms = cfmedb()["vms"]
            falsey = False  # This is to prevent a lint error with ==False
            vmlist = list(cfmedb().session.query(vms.name)
                          .join(ext_management_systems, vms.ems_id == ext_management_systems.id)
                          .filter(ext_management_systems.name == self.name)
                          .filter(vms.template == falsey))
            return len(vmlist)
        return int(self.get_detail("Relationships", "Instances"))

    @property
    def exists(self):
        ems = cfmedb()['ext_management_systems']
        provs = (prov[0] for prov in cfmedb().session.query(ems.name))
        if self.name in provs:
            return True
        else:
            return False

    @property
    def _all_available_policy_profiles(self):
        pp_rows_locator = "//table/tbody/tr/td[@class='standartTreeImage']"\
            "/img[contains(@src, 'policy_profile')]/../../td[@class='standartTreeRow']"
        return sel.elements(pp_rows_locator)

    def _is_policy_profile_row_checked(self, row):
        return "Check" in row.find_element_by_xpath("../td[@width='16px']/img").get_attribute("src")

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
        sel.force_navigate('clouds_provider_policy_assignment', context={'provider': self})
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
        sel.force_navigate('clouds_provider_policy_assignment', context={'provider': self})
        return self._unassigned_policy_profiles

    def _assign_unassign_policy_profiles(self, assign, *policy_profile_names):
        """ Assign or unassign Policy Profiles to this Provider. DRY method

        Args:
            assign: Whether this method assigns or unassigns policy profiles.
            policy_profile_names: :py:class:`str` with Policy Profile's name. After Control/Explorer
                coverage goes in, PolicyProfile object will be also passable.
        """
        sel.force_navigate('clouds_provider_policy_assignment', context={'provider': self})
        for policy_profile in policy_profile_names:
            if assign:
                manage_policies_tree.check_node(policy_profile)
            else:
                manage_policies_tree.uncheck_node(policy_profile)
        sel.move_to_element('#tP')
        form_buttons.save()

    def assign_policy_profiles(self, *policy_profile_names):
        """ Assign Policy Profiles to this Provider.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        self._assign_unassign_policy_profiles(True, *policy_profile_names)

    def unassign_policy_profiles(self, *policy_profile_names):
        """ Unssign Policy Profiles to this Provider.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        self._assign_unassign_policy_profiles(False, *policy_profile_names)


class EC2Provider(Provider):
    def __init__(self, name=None, credentials=None, zone=None, key=None, region=None):
        super(EC2Provider, self).__init__(name=name, credentials=credentials,
                                          zone=zone, key=key)
        self.region = region

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Amazon EC2',
                'amazon_region_select': sel.ByValue(kwargs.get('region'))}


class OpenStackProvider(Provider):
    def __init__(self, name=None, credentials=None, zone=None, key=None, hostname=None,
                 ip_address=None, api_port=None):
        super(OpenStackProvider, self).__init__(name=name, credentials=credentials,
                                                zone=zone, key=key)
        self.hostname = hostname
        self.ip_address = ip_address
        self.api_port = api_port

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'OpenStack',
                'hostname_text': kwargs.get('hostname'),
                'api_port': kwargs.get('api_port'),
                'ipaddress_text': kwargs.get('ip_address')}


@fill.method((Form, Provider.Credential))
def _fill_credential(form, cred, validate=None):
    """How to fill in a credential (either amqp or default).  Validates the
    credential if that option is passed in.
    """
    if cred.amqp:
        fill(credential_form, {'amqp_button': True,
                               'amqp_principal': cred.principal,
                               'amqp_secret': cred.secret,
                               'amqp_verify_secret': cred.verify_secret,
                               'validate_btn': validate})
    else:
        fill(credential_form, {'default_principal': cred.principal,
                               'default_secret': cred.secret,
                               'default_verify_secret': cred.verify_secret,
                               'validate_btn': validate})
    if validate:
        flash.assert_no_errors()


def get_all_providers(do_not_navigate=False):
    """Returns list of all providers"""
    if not do_not_navigate:
        sel.force_navigate('clouds_providers')
    providers = set([])
    link_marker = version.pick({
        version.LOWEST: "ext_management_system",
        "5.2.5": "ems_cloud"
    })
    for page in paginator.pages():
        for title in sel.elements("//div[@id='quadicon']/../../../tr/td/a[contains(@href,"
                "'{}/show')]".format(link_marker)):
            providers.add(sel.get_attribute(title, "title"))
    return providers


def get_credentials_from_config(credential_config_name):
    creds = conf.credentials[credential_config_name]
    return Provider.Credential(principal=creds['username'],
                               secret=creds['password'])


def get_from_config(provider_config_name):
    """
    Creates a Provider object given a yaml entry in cfme_data.

    Usage:
        get_from_config('ec2east')

    Returns: A Provider object that has methods that operate on CFME
    """

    prov_config = conf.cfme_data.get('management_systems', {})[provider_config_name]
    credentials = get_credentials_from_config(prov_config['credentials'])
    prov_type = prov_config.get('type')
    if prov_type == 'ec2':
        return EC2Provider(name=prov_config['name'],
                           region=prov_config['region'],
                           credentials=credentials,
                           zone=prov_config['server_zone'],
                           key=provider_config_name)
    elif prov_type == 'openstack':
        return OpenStackProvider(name=prov_config['name'],
                                 hostname=prov_config['hostname'],
                                 ip_address=prov_config['ipaddress'],
                                 api_port=prov_config['port'],
                                 credentials=credentials,
                                 zone=prov_config['server_zone'],
                                 key=provider_config_name)
    else:
        raise UnknownProviderType('{} is not a known cloud provider type'.format(prov_type))


def discover(credential, cancel=False):
    """
    Discover cloud providers. Note: only starts discovery, doesn't
    wait for it to finish.

    Args:
      credential (cfme.Credential):  Amazon discovery credentials.
      cancel (boolean):  Whether to cancel out of the discover UI.
    """
    sel.force_navigate('clouds_provider_discover')
    form_data = {}
    if credential:
        form_data.update({'username': credential.principal,
                          'password': credential.secret,
                          'password_verify': credential.verify_secret})
    fill(discover_form, form_data,
         action=form_buttons.cancel if cancel else discover_form.start_button,
         action_always=True)


def wait_for_a_provider():
    sel.force_navigate('clouds_providers')
    logger.info('Waiting for a provider to appear...')
    wait_for(paginator.rec_total, fail_condition=None, message="Wait for any provider to appear",
             num_sec=1000, fail_func=sel.refresh)


def wait_for_provider_delete(provider):
    sel.force_navigate('clouds_providers')
    quad = Quadicon(provider.name, 'cloud_prov')
    logger.info('Waiting for a provider to delete...')
    wait_for(lambda prov: not sel.is_displayed(prov), func_args=[quad], fail_condition=False,
             message="Wait provider to disappear", num_sec=1000, fail_func=sel.refresh)
