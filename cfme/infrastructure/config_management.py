from functools import partial
from cached_property import cached_property

import ui_navigate as nav

import cfme
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.flash as flash
import cfme.web_ui.menu
import cfme.web_ui.tabstrip as tabs
import cfme.web_ui.toolbar as tb
from cfme.web_ui import (
    accordion, Quadicon, Form, Input, fill, form_buttons, SplitTable, mixins
)
from utils import version, conf
from utils.log import logger
from utils.pretty import Pretty
from utils.update import Updateable
from utils.wait import wait_for


properties_form = Form(
    fields=[
        ('name_text', Input('name')),
        ('url_text', Input('url')),
        ('ssl_checkbox', Input('verify_ssl'))
    ])

credential_form = Form(
    fields=[
        ('principal_text', Input('log_userid')),
        ('secret_pass', Input('log_password')),
        ('verify_secret_pass', Input('log_verify')),
        ('validate_btn', form_buttons.validate)
    ])

list_table = SplitTable(
    header_data=("//div[@id='list_grid']/div[@class='xhdr']/table/tbody", 1),
    body_data=("//div[@id='list_grid']/div[@class='objbox']/table/tbody", 1),
)

add_manager_btn = form_buttons.FormButton('Add')
edit_manager_btn = form_buttons.FormButton('Save changes')
cfg_btn = partial(tb.select, 'Configuration')

nav.add_branch(
    'infrastructure_config_management',
    {
        'infrastructure_config_managers':
        [
            lambda _: (accordion.tree('Providers',
                version.pick({version.LOWEST: 'All Red Hat Satellite Providers',
                              version.UPSTREAM: 'All Foreman Providers'})),
                tb.select('Grid View')),
            {
                'infrastructure_config_manager_new':
                lambda _: cfg_btn('Add a new Provider'),
                'infrastructure_config_manager':
                [
                    lambda ctx: sel.check(
                        Quadicon(
                            '{} Configuration Manager'
                            .format(ctx['manager'].name), None).checkbox),
                    {
                        'infrastructure_config_manager_edit':
                        lambda _: cfg_btn('Edit Selected item'),
                        'infrastructure_config_manager_refresh':
                        lambda _: cfg_btn('Refresh Relationships and Power states',
                                  invokes_alert=True),
                        'infrastructure_config_manager_remove':
                        lambda _: cfg_btn('Remove selected items from the VMDB', invokes_alert=True)
                    }
                ],
                'infrastructure_config_manager_detail':
                [
                    lambda ctx: sel.click(
                        Quadicon('{} Configuration Manager'.format(ctx['manager'].name), None)),
                    {
                        'infrastructure_config_manager_edit_detail':
                        lambda _: cfg_btn('Edit this Provider'),
                        'infrastructure_config_manager_refresh_detail':
                        lambda _: cfg_btn('Refresh Relationships and Power states',
                                  invokes_alert=True),
                        'infrastructure_config_manager_remove_detail':
                        lambda _: cfg_btn('Remove this Provider from the VMDB', invokes_alert=True),
                        'infrastructure_config_manager_config_profile':
                        lambda ctx: list_table.click_cell('Description', ctx['profile'].name)
                    }
                ]
            }
        ],
        'infrastructure_config_systems':
        [
            lambda _: accordion.tree('Configured Systems',
                version.pick({version.LOWEST: 'All Red Hat Satellite Configured Systems',
                              version.UPSTREAM: 'All Foreman Configured Systems'})),
            {
                'infrastructure_config_system':
                [
                    lambda ctx: (tb.select('Grid View'),
                    sel.click(Quadicon(ctx['system'].name, None))),
                    {
                        'infrastructure_config_system_provision':
                        lambda _: cfg_btn('Provision Configured System'),
                        'infrastructure_config_system_edit_tags':
                        lambda _: cfg_btn('Edit Tags')
                    }
                ]
            }
        ]
    }
)


class ConfigManager(Updateable, Pretty):
    """
    Configuration manager object (Foreman, RH Satellite)

    Args:
        name: Name of the config. manager
        url: URL, hostname or IP of the config. manager
        ssl: Boolean value; `True` if SSL certificate validity should be checked, `False` otherwise
        credentials: Credentials to access the config. manager
        key: Key to access the cfme_data yaml data (same as `name` if not specified)

    Usage:
        .. code-block:: python

            cfg_mgr = ConfigManager('my_foreman', 'my-foreman.example.com', False,
                                ConfigManager.Credential(principal='admin', secret='testing'))
            cfg_mgr.create()
    """

    pretty_attr = ['name', 'url']

    def __init__(self, name, url, ssl, credentials, key=None):
        self.name = name
        self.url = url
        self.ssl = ssl
        self.credentials = credentials
        self.key = key or name

    def _form_mapping(self, **kwargs):
        return {'name_text': kwargs.get('name'),
                'url_text': kwargs.get('url'),
                'ssl_checkbox': kwargs.get('ssl')}

    class Credential(cfme.Credential, Updateable):
        pass

    def _submit(self, cancel, submit_button):
        if cancel:
            form_buttons.cancel()
        else:
            submit_button()
            flash.assert_no_errors()

    def navigate(self):
        """Navigates to the manager's detail page"""
        sel.force_navigate('infrastructure_config_manager_detail', context={'manager': self})

    @cached_property
    def type(self):
        """Returns presumed type of the manager based on CFME version

        Note:
            We cannot actually know the type of the provider from the UI.
            This represents the supported type by CFME version and is to be used in navigation.
        """
        return version.pick({version.LOWEST: 'Red Hat Satellite', version.LATEST: 'Foreman'})

    def create(self, cancel=False, validate_credentials=True, validate=True, force=False):
        """Creates the manager through UI

        Args:
            cancel (bool): Whether to cancel out of the creation.  The cancel is done
                after all the information present in the manager has been filled in the UI.
            validate_credentials (bool): Whether to validate credentials - if True and the
                credentials are invalid, an error will be raised.
            validate (bool): Whether we want to wait for the manager's data to load
                and show up in it's detail page. True will also wait, False will only set it up.
            force (bool): Whether to force the creation even if the manager already exists.
                True will try anyway; False will check for its existence and leave, if present.
        """
        def config_profiles_loaded():
            config_profiles_names = [prof.name for prof in self.config_profiles]
            logger.info(
                "UI: {}\nYAML: {}"
                .format(set(config_profiles_names), set(self.yaml_data['config_profiles'])))
            return all(
                [cp in config_profiles_names for cp in self.yaml_data['config_profiles']])

        if not force and self.exists:
            return
        sel.force_navigate('infrastructure_config_manager_new')
        fill(properties_form, self._form_mapping(**self.__dict__))
        fill(credential_form, self.credentials, validate=validate_credentials)
        self._submit(cancel, add_manager_btn)
        if not cancel:
            flash_msg = '{} Provider "{}" was added'.format(self.type, self.name)
            flash.assert_message_match(flash_msg)
            if validate:
                wait_for(
                    func=config_profiles_loaded,
                    fail_func=self.refresh_relationships,
                    handle_exception=True,
                    num_sec=180, delay=30)

    def update(self, updates, cancel=False, validate_credentials=False):
        """Updates the manager through UI

        args:
            updates (dict): Data to change.
            cancel (bool): Whether to cancel out of the update.  The cancel is done
                after all the new information has been filled in the UI.
            validate_credentials (bool): Whether to validate credentials - if True and the
                credentials are invalid, an error will be raised.

        Note:
            utils.update use is recommended over use of this method.
        """
        sel.force_navigate('infrastructure_config_manager_edit', context={'manager': self})
        fill(properties_form, self._form_mapping(**updates))
        fill(credential_form, updates.get('credentials', None), validate=validate_credentials)
        self._submit(cancel, edit_manager_btn)
        name = updates['name'] or self.name
        if not cancel:
            flash.assert_message_match('{} Provider "{}" was updated'.format(self.type, name))

    def delete(self, cancel=False, wait_deleted=True, force=False):
        """Deletes the manager through UI

        Args:
            cancel (bool): Whether to cancel out of the deletion, when the alert pops up.
            wait_deleted (bool): Whether we want to wait for the manager to disappear from the UI.
                True will wait; False will only delete it and move on.
            force (bool): Whether to try to delete the manager even though it doesn't exist.
                True will try to delete it anyway; False will check for its existence and leave,
                if not present.
        """
        if not force and not self.exists:
            return
        sel.force_navigate('infrastructure_config_manager_remove', context={'manager': self})
        sel.handle_alert(cancel)
        if not cancel:
            flash.assert_message_match(
                'Delete initiated for 1 Provider from the CFME Database')
            if wait_deleted:
                wait_for(func=lambda: self.exists, fail_condition=True, delay=15, num_sec=60)

    @property
    def exists(self):
        """Returns whether the manager exists in the UI or not"""
        sel.force_navigate('infrastructure_config_managers')
        if (Quadicon.any_present() and
                Quadicon('{} Configuration Manager'.format(self.name), None).exists):
            return True
        return False

    def refresh_relationships(self, cancel=False):
        """Refreshes relationships and power states of this manager"""
        sel.force_navigate('infrastructure_config_manager_refresh', context={'manager': self})
        sel.handle_alert(cancel)
        if not cancel:
            flash.assert_message_match(
                'Refresh {0} initiated for 1 Provider ({0}) from the CFME Database'
                .format(self.type))

    @property
    def config_profiles(self):
        """Returns 'ConfigProfile' configuration profiles (hostgroups) available on this manager"""
        self.navigate()
        return [ConfigProfile(row['description'].text, self) for row in list_table.rows()]

    @property
    def systems(self):
        """Returns 'ConfigSystem' configured systems (hosts) available on this manager"""
        return reduce(lambda x, y: x + y, [prof.systems for prof in self.config_profiles])

    @property
    def yaml_data(self):
        """Returns yaml data for this manager"""
        return conf.cfme_data.configuration_managers[self.key]

    @classmethod
    def load_from_yaml(cls, key):
        """Returns 'ConfigManager' object loaded from yamls, based on its key"""
        data = conf.cfme_data.configuration_managers[key]
        creds = conf.credentials[data['credentials']]
        return cls(
            name=data['name'],
            url=data['url'],
            ssl=data['ssl'],
            credentials=cls.Credential(
                principal=creds['username'], secret=creds['password']),
            key=key)


@fill.method((Form, ConfigManager.Credential))
def _fill_credential(form, cred, validate=None):
    """How to fill in a credential. Validates the credential if that option is passed in."""
    fill(credential_form, {'principal_text': cred.principal,
                           'secret_pass': cred.secret,
                           'verify_secret_pass': cred.verify_secret,
                           'validate_btn': validate})
    if validate:
        flash.assert_no_errors()


class ConfigProfile(Pretty):
    """Configuration profile object (foreman-side hostgroup)

    Args:
        name: Name of the profile
        manager: ConfigManager object which this profile is bound to
    """
    pretty_attr = ['name', 'manager']

    def __init__(self, name, manager):
        self.name = name
        self.manager = manager

    def navigate(self):
        """Navigates to the profile's detail page"""
        sel.force_navigate('infrastructure_config_manager_config_profile',
            context={'manager': self.manager, 'profile': self})

    @property
    def systems(self):
        """Returns 'ConfigSystem' objects that are active under this profile"""
        self.navigate()
        # ajax wait doesn't work here
        _header_loc = "//div[contains(@class, 'dhtmlxInfoBarLabel')"\
                      " and contains(normalize-space(text()), 'Configured Systems')]"
        sel.wait_for_element(_header_loc)
        # Unassigned config profile has no tabstrip
        if "unassigned" not in self.name.lower():
            tabs.select_tab("Configured Systems")
        if sel.is_displayed(list_table):
            return [ConfigSystem(row['description'].text, self) for row in list_table.rows()]
        return list()


class ConfigSystem(Pretty):

    pretty_attr = ['name', 'manager_key']

    def __init__(self, name, profile):
        self.name = name
        self.profile = profile

    def navigate(self):
        """Navigates to the system's detail page"""
        sel.force_navigate('infrastructure_config_system',
            context={'system': self.profile.manager, 'profile': self.profile, 'system': self})

    def tag(self, tag):
        """Tags the system by given tag"""
        self.navigate()
        # Workaround for BZ#1241867
        tb.select('Policy', 'Edit Tags')
        fill(mixins.tag_form, {'category': 'Cost Center *', 'tag': 'Cost Center 001'})
        # ---
        mixins.add_tag(tag, navigate=False)

    def untag(self, tag):
        """Removes the selected tag off the system"""
        self.navigate()
        mixins.remove_tag(tag)

    @property
    def tags(self):
        """Returns a list of this system's active tags"""
        self.navigate()
        return mixins.get_tags()
