from functools import partial

from utils import conf
from cfme.exceptions import (
    ProviderHasNoKey, HostStatsNotContains, ProviderHasNoProperty
)
import cfme
from cfme.web_ui import flash, Quadicon, CheckboxTree, Region, fill, Form, Input
from cfme.web_ui import toolbar as tb
from cfme.web_ui import form_buttons
import cfme.fixtures.pytest_selenium as sel
from utils.browser import ensure_browser_open
from utils.db import cfmedb
from utils.log import logger
from utils.signals import fire
from utils.wait import wait_for, RefreshTimer
from utils.stats import tol_check
from utils.update import Updateable
from utils import version


cfg_btn = partial(tb.select, 'Configuration')

manage_policies_tree = CheckboxTree(
    {
        version.LOWEST: "//div[@id='treebox']/div/table",
        "5.3": "//div[@id='protect_treebox']/ul"
    }
)

details_page = Region(infoblock_type='detail')

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
        ('candu_button', "//div[@id='auth_tabs']/ul/li/a[@href='#metrics']"),
        ('candu_principal', Input("metrics_userid")),
        ('candu_secret', Input("metrics_password")),
        ('candu_verify_secret', Input("metrics_verify")),
        ('validate_btn', form_buttons.validate)
    ])


class BaseProvider(object):
    class Credential(cfme.Credential, Updateable):
        """Provider credentials

           Args:
             **kwargs: If using amqp type credential, amqp = True"""

        def __init__(self, **kwargs):
            super(BaseProvider.Credential, self).__init__(**kwargs)
            self.amqp = kwargs.get('amqp')
            self.candu = kwargs.get('candu')
            self.domain = kwargs.get('domain')

    @property
    def data(self):
        return self.get_yaml_data()

    @property
    def mgmt(self):
        return self.get_mgmt_system()

    @property
    def type(self):
        return self.data['type']

    @property
    def version(self):
        return self.data['version']

    def get_yaml_data(self):
        """ Returns yaml data for this provider.
        """
        if hasattr(self, 'provider_data') and self.provider_data is not None:
            return self.provider_data
        elif self.key is not None:
            return conf.cfme_data['management_systems'][self.key]
        else:
            raise ProviderHasNoKey('Provider %s has no key, so cannot get yaml data', self.name)

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
            raise ProviderHasNoKey('Provider %s has no key, so cannot get mgmt system')

    def _submit(self, cancel, submit_button):
        if cancel:
            form_buttons.cancel()
            # sel.wait_for_element(page.configuration_btn)
        else:
            submit_button()
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
        sel.force_navigate('{}_provider_new'.format(self.page_name))
        fill(self.properties_form, self._form_mapping(True, **self.__dict__))
        for cred in self.credentials:
            fill(self.credential_form, self.credentials[cred], validate=validate_credentials)
        self._submit(cancel, self.add_provider_button)
        fire("providers_changed")
        if not cancel:
            flash.assert_message_match('{} Providers "{}" was saved'.format(self.string_name,
                                                                            self.name))

    def update(self, updates, cancel=False, validate_credentials=False):
        """
        Updates a provider in the UI.  Better to use utils.update.update context
        manager than call this directly.

        Args:
           updates (dict): fields that are changing.
           cancel (boolean): whether to cancel out of the update.
        """

        sel.force_navigate('{}_provider_edit'.format(self.page_name), context={'provider': self})
        fill(self.properties_form, self._form_mapping(**updates))
        for cred in self.credentials:
            fill(self.credential_form, updates.get('credentials', {}).get(cred, None),
                 validate=validate_credentials)
        self._submit(cancel, form_buttons.save)
        name = updates['name'] or self.name
        if not cancel:
            flash.assert_message_match('{} Provider "{}" was saved'.format(self.string_name, name))

    def delete(self, cancel=True):
        """
        Deletes a provider from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        sel.force_navigate('{}_provider'.format(self.page_name), context={'provider': self})
        cfg_btn('Remove this {} Provider from the VMDB'.format(self.string_name),
            invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        fire("providers_changed")
        if not cancel:
            flash.assert_message_match(
                'Delete initiated for 1 {} Provider from the CFME Database'.format(
                    self.string_name))

    def delete_if_exists(self, *args, **kwargs):
        """Combines ``.exists`` and ``.delete()`` as a shortcut for ``request.addfinalizer``"""
        if self.exists:
            self.delete(*args, **kwargs)

    def wait_for_creds_ok(self):
        """Waits for provider's credentials to become O.K. (circumvents the summary rails exc.)"""
        self.refresh_provider_relationships(from_list_view=True)

        def _wait_f():
            sel.force_navigate("{}_providers".format(self.page_name))
            q = Quadicon(self.name, self.quad_name)
            creds = q.creds
            return creds == "checkmark"

        wait_for(_wait_f, num_sec=300, delay=5, message="credentials of {} ok!".format(self.name))

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
            sel.force_navigate('{}_provider'.format(self.page_name), context={'provider': self})

        # Initial bullet check
        if self._do_stats_match(client, self.STATS_TO_MATCH, db=db):
            client.disconnect()
            return
        else:
            # Set off a Refresh Relationships
            sel.force_navigate('{}_provider'.format(self.page_name), context={'provider': self})
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
                sel.force_navigate('{}_provider'.format(self.page_name), context={'provider': self})
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
            return int(self.get_detail("Relationships", self.template_name))

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
        return int(self.get_detail("Relationships", self.vm_name))

    @property
    def exists(self):
        ems = cfmedb()['ext_management_systems']
        provs = (prov[0] for prov in cfmedb().session.query(ems.name))
        if self.name in provs:
            return True
        else:
            return False

    def wait_for_delete(self):
        sel.force_navigate('{}_providers'.format(self.page_name))
        quad = Quadicon(self.name, self.quad_name)
        logger.info('Waiting for a provider to delete...')
        wait_for(lambda prov: not sel.is_displayed(prov), func_args=[quad], fail_condition=False,
                 message="Wait provider to disappear", num_sec=1000, fail_func=sel.refresh)

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

    def _assign_unassign_policy_profiles(self, assign, *policy_profile_names):
        """ Assign or unassign Policy Profiles to this Provider. DRY method

        See :py:func:`assign_policy_profiles` and :py:func:`assign_policy_profiles`

        Args:
            assign: Whether this method assigns or unassigns policy profiles.
            policy_profile_names: :py:class:`str` with Policy Profile's name. After Control/Explorer
                coverage goes in, PolicyProfile object will be also passable.
        """
        sel.force_navigate('{}_provider_policy_assignment'.format(self.page_name),
            context={'provider': self})
        for policy_profile in policy_profile_names:
            if assign:
                manage_policies_tree.check_node(policy_profile)
            else:
                manage_policies_tree.uncheck_node(policy_profile)
        sel.move_to_element('#tP')
        form_buttons.save()

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
        sel.force_navigate('{}_provider_policy_assignment'.format(self.page_name),
            context={'provider': self})
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
        sel.force_navigate('{}_provider_policy_assignment'.format(self.page_name),
            context={'provider': self})
        return self._unassigned_policy_profiles

    @property
    def _all_available_policy_profiles(self):
        pp_rows_locator = "//table/tbody/tr/td[@class='standartTreeImage']"\
            "/img[contains(@src, 'policy_profile')]/../../td[@class='standartTreeRow']"
        return sel.elements(pp_rows_locator)

    def _is_policy_profile_row_checked(self, row):
        return "Check" in row.find_element_by_xpath("../td[@width='16px']/img").get_attribute("src")

    def refresh_provider_relationships(self, from_list_view=False):
        """Clicks on Refresh relationships button in provider"""
        if from_list_view:
            sel.force_navigate("{}_providers".format(self.page_name))
            sel.check(Quadicon(self.name, self.quad_name).checkbox())
        else:
            sel.force_navigate('{}_provider'.format(self.page_name), context={"provider": self})
        tb.select("Configuration", "Refresh Relationships and Power States", invokes_alert=True)
        sel.handle_alert(cancel=False)

    def _load_details(self):
        if not self._on_detail_page():
            sel.force_navigate('{}_provider'.format(self.page_name), context={'provider': self})

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific provider.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        self._load_details()
        return details_page.infoblock.text(*ident)

    def load_all_provider_instances(self):
        self.load_all_provider_vms()

    def load_all_provider_vms(self):
        """ Loads the list of instances that are running under the provider.

        If it could click through the link in infoblock, returns ``True``. If it sees that the
        number of instances is 0, it returns ``False``.
        """
        sel.force_navigate('{}_provider'.format(self.page_name), context={'provider': self})
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
        sel.force_navigate('{}_provider'.format(self.page_name), context={'provider': self})
        if details_page.infoblock.text("Relationships", self.template_name) == "0":
            return False
        else:
            sel.click(details_page.infoblock.element("Relationships", self.template_name))
            return True

    """
    From cloud
    def _on_detail_page(self):
        "" Returns ``True`` if on the providers detail page, ``False`` if not.""
        return sel.is_displayed('//div[@class="dhtmlxInfoBarLabel-2"][contains(., "%s")]'
                                % self.name)
    """

    def _on_detail_page(self):
        """ Returns ``True`` if on the providers detail page, ``False`` if not."""
        ensure_browser_open()
        return sel.is_displayed(
            '//div[@class="dhtmlxInfoBarLabel-2"][contains(., "%s (Summary)")]' % self.name)

    # @classmethod
    # def get_from_config(provider_key):
    #    return utils.providers.get_crud(provider_key)


@fill.method((Form, BaseProvider.Credential))
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
    elif cred.candu:
        fill(credential_form, {'candu_button': True,
                               'candu_principal': cred.principal,
                               'candu_secret': cred.secret,
                               'candu_verify_secret': cred.verify_secret,
                               'validate_btn': validate})
    else:
        if cred.domain:
            principal = r'{}\{}'.format(cred.domain, cred.principal)
        else:
            principal = cred.principal
        fill(credential_form, {'default_principal': principal,
                               'default_secret': cred.secret,
                               'default_verify_secret': cred.verify_secret,
                               'validate_btn': validate})
    if validate:
        flash.assert_no_errors()


def cleanup_vm(vm_name, provider):
    try:
        logger.info('Cleaning up VM %s on provider %s' % (vm_name, provider.key))
        provider.mgmt.delete_vm(vm_name)
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s' % (vm_name, provider.key))
