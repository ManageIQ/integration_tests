from functools import partial
from cached_property import cached_property
from navmazing import NavigateToSibling, NavigateToAttribute


import cfme
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.flash as flash
import cfme.web_ui.tabstrip as tabs
import cfme.web_ui.toolbar as tb
from cfme.web_ui import (
    accordion, Quadicon, Form, Input, fill, form_buttons, mixins, Table, Region,
    AngularSelect, match_location
)
from utils import version, conf
from utils.appliance.endpoints.ui import navigator, CFMENavigateStep, navigate_to
from utils.appliance import Navigatable
from utils.log import logger
from utils.pretty import Pretty
from utils.update import Updateable
from utils.wait import wait_for


properties_form = Form(
    fields=[
        ('name_text', Input('name')),
        ('type_select', AngularSelect("provider_type")),
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


def cfm_mgr_table():
    return Table("//div[@id='main_div']//div[@id='list_grid']/table")


page = Region(locators={
    'list_table_config_profiles': cfm_mgr_table(),
    'list_table_config_systems': cfm_mgr_table()})

add_manager_btn = form_buttons.FormButton('Add')
edit_manager_btn = form_buttons.FormButton('Save changes')
cfg_btn = partial(tb.select, 'Configuration')


match_page = partial(match_location, controller='provider_foreman',
                     title='Red Hat Satellite Provider')


class ConfigManager(Updateable, Pretty, Navigatable):
    """
    This is base class for Configuration manager objects (Red Hat Satellite, Foreman, Ansible Tower)

    Args:
        name: Name of the config. manager
        url: URL, hostname or IP of the config. manager
        ssl: Boolean value; `True` if SSL certificate validity should be checked, `False` otherwise
        credentials: Credentials to access the config. manager
        key: Key to access the cfme_data yaml data (same as `name` if not specified)

    Usage:
        Use Satellite or AnsibleTower classes instead.
    """

    pretty_attr = ['name', 'url']
    type = None

    def __init__(self, name=None, url=None, ssl=None, credentials=None, key=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.url = url
        self.ssl = ssl
        self.credentials = credentials
        self.key = key or name

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and self.type,
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
            # Workaround - without this, validation of provider failed
            config_profiles_names = [prof.name for prof in self.config_profiles]
            logger.info(
                "UI: %s\nYAML: %s",
                set(config_profiles_names), set(self.yaml_data['config_profiles']))
            return all(
                [cp in config_profiles_names for cp in self.yaml_data['config_profiles']])

        if not force and self.exists:
            return
        navigate_to(self, 'Add')
        fill(properties_form, self._form_mapping(create=True, **self.__dict__))
        fill(credential_form, self.credentials, validate=validate_credentials)
        self._submit(cancel, add_manager_btn)
        if not cancel:
            flash.assert_message_match(self._refresh_flash_msg)
            if validate:
                try:
                    self.yaml_data['config_profiles']
                except KeyError as e:
                    logger.exception(e)
                    raise

                wait_for(
                    config_profiles_loaded,
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
        navigate_to(self, 'Edit')
        # Workaround - without this, update was failing on downstream appliance
        sel.wait_for_ajax()
        sel.wait_for_element(properties_form.name_text)

        fill(properties_form, self._form_mapping(**updates))
        fill(credential_form, updates.get('credentials', None), validate=validate_credentials)
        self._submit(cancel, edit_manager_btn)
        name = updates['name'] or self.name
        if not cancel:
            flash.assert_message_match('{} Provider "{}" was updated'.format(self.type, name))

        self.__dict__.update(**updates)

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
        navigate_to(self, 'All')
        sel.check(Quadicon(self.quad_name, None).checkbox())
        item_text = version.pick({'5.6': 'Remove selected items from the VMDB',
                                  '5.7': 'Remove selected items'})
        cfg_btn(item_text, invokes_alert=True)

        sel.handle_alert(cancel)
        if not cancel:
            flash_msg = version.pick({'5.6': 'Delete initiated for 1 provider',
                                      '5.7': 'Delete initiated for 1 Provider'})

            flash.assert_message_match(flash_msg)
            if wait_deleted:
                wait_for(func=lambda: self.exists, fail_condition=True, delay=15, num_sec=60)

    @property
    def _refresh_flash_msg(self):
        return 'Refresh Provider initiated for 1 provider ({})'.format(self.type)

    @property
    def exists(self):
        """Returns whether the manager exists in the UI or not"""
        navigate_to(self, 'All')
        if (Quadicon.any_present() and
                Quadicon(self.quad_name, None).exists):
            return True
        return False

    def refresh_relationships(self, cancel=False):
        """Refreshes relationships and power states of this manager"""
        navigate_to(self, 'All')

        sel.check(Quadicon(self.quad_name, None).checkbox())
        cfg_btn('Refresh Relationships and Power states', invokes_alert=True)

        sel.handle_alert(cancel)
        if not cancel:
            flash.assert_message_match(self._refresh_flash_msg)

    def _does_profile_exist(self):
        return sel.is_displayed(page.list_table_config_profiles)

    @property
    def config_profiles(self):
        """Returns 'ConfigProfile' configuration profiles (hostgroups) available on this manager"""
        navigate_to(self, 'Details')
        tb.select('List View')
        wait_for(self._does_profile_exist, num_sec=300, delay=20, fail_func=sel.refresh)
        return [ConfigProfile(row['name'].text, self) for row in
                page.list_table_config_profiles.rows()]

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

    @property
    def quad_name(self):
        return '{} Configuration Manager'.format(self.name)


def get_config_manager_from_config(cfg_mgr_key):
    cfg_mgr = conf.cfme_data.get('configuration_managers', {})[cfg_mgr_key]
    if cfg_mgr['type'] == 'satellite':
        return Satellite.load_from_yaml(cfg_mgr_key)
    elif cfg_mgr['type'] == 'ansible':
        return AnsibleTower.load_from_yaml(cfg_mgr_key)
    else:
        raise Exception("Unknown configuration manager key")


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
    pretty_attrs = ['name', 'manager']

    def __init__(self, name, manager):
        self.name = name
        self.manager = manager

    @property
    def systems(self):
        """Returns 'ConfigSystem' objects that are active under this profile"""
        navigate_to(self, 'Details')
        # ajax wait doesn't work here
        _title_loc = "//span[contains(@id, 'explorer_title_text') " \
                     "and contains(normalize-space(text()), 'Configured Systems')]"
        sel.wait_for_element(_title_loc)

        # Unassigned config profile has no tabstrip
        if "unassigned" not in self.name.lower():
            tabs.select_tab("Configured Systems")

        if sel.is_displayed(page.list_table_config_systems):
            row_key = 'hostname'
            return [ConfigSystem(row[row_key].text, self) for row in
                    page.list_table_config_systems.rows()]
        return list()


class ConfigSystem(Pretty):

    pretty_attrs = ['name', 'manager_key']

    def __init__(self, name, profile):
        self.name = name
        self.profile = profile

    def tag(self, tag):
        """Tags the system by given tag"""
        navigate_to(self, 'EditTags')
        fill(mixins.tag_form, {'category': 'Cost Center *', 'tag': 'Cost Center 001'})
        # ---
        mixins.add_tag(tag, navigate=False)

    def untag(self, tag):
        """Removes the selected tag off the system"""
        navigate_to(self, 'EditTags')
        mixins.remove_tag(tag)

    @property
    def tags(self):
        """Returns a list of this system's active tags"""
        navigate_to(self, 'EditTags')
        return mixins.get_tags()


class Satellite(ConfigManager):
    """
    Configuration manager object (Red Hat Satellite, Foreman)

    Args:
        name: Name of the Satellite/Foreman configuration manager
        url: URL, hostname or IP of the configuration manager
        ssl: Boolean value; `True` if SSL certificate validity should be checked, `False` otherwise
        credentials: Credentials to access the config. manager
        key: Key to access the cfme_data yaml data (same as `name` if not specified)

    Usage:
        Create provider:
        .. code-block:: python

            satellite_cfg_mgr = Satellite('my_satellite', 'my-satellite.example.com',
                                ssl=False, ConfigManager.Credential(principal='admin',
                                secret='testing'), key='satellite_yaml_key')
            satellite_cfg_mgr.create()

        Update provider:
        .. code-block:: python

            with update(satellite_cfg_mgr):
                satellite_cfg_mgr.name = 'new_satellite_name'

        Delete provider:
        .. code-block:: python

            satellite_cfg_mgr.delete()
    """

    def __init__(self, name=None, url=None, ssl=None, credentials=None, key=None):
        super(Satellite, self).__init__(name=name, url=url, ssl=ssl, credentials=credentials,
                                        key=key)
        self.name = name
        self.url = url
        self.ssl = ssl
        self.credentials = credentials
        self.key = key or name

    @cached_property
    def type(self):
        """Returns presumed type of the manager based on CFME version

        Note:
            We cannot actually know the type of the provider from the UI.
            This represents the supported type by CFME version and is to be used in navigation.
            """
        return version.pick({version.LOWEST: 'Red Hat Satellite', version.LATEST: 'Foreman'})


class AnsibleTower(ConfigManager):
    """
    Configuration manager object (Ansible Tower)

    Args:
        name: Name of the Ansible Tower configuration manager
        url: URL, hostname or IP of the configuration manager
        ssl: Boolean value; `True` if SSL certificate validity should be checked, `False` otherwise
        credentials: Credentials to access the config. manager
        key: Key to access the cfme_data yaml data (same as `name` if not specified)

    Usage:
        Create provider:
        .. code-block:: python

            tower_cfg_mgr = AnsibleTower('my_tower', 'https://my-tower.example.com/api/v1',
                                ssl=False, ConfigManager.Credential(principal='admin',
                                secret='testing'), key='tower_yaml_key')
            tower_cfg_mgr.create()

        Update provider:
        .. code-block:: python

            with update(tower_cfg_mgr):
                tower_cfg_mgr.name = 'new_tower_name'

        Delete provider:
        .. code-block:: python

            tower_cfg_mgr.delete()
    """

    type = 'Ansible Tower'

    def __init__(self, name=None, url=None, ssl=None, credentials=None, key=None):
        super(AnsibleTower, self).__init__(name=name, url=url, ssl=ssl, credentials=credentials,
                                           key=key)
        self.name = name
        self.url = url
        self.ssl = ssl
        self.credentials = credentials
        self.key = key or name


@navigator.register(ConfigManager, 'All')
class MgrAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Configuration', 'Configuration Management')(None)

    def resetter(self):
        accordion.tree('Providers', 'All Configuration Manager Providers')
        tb.select('Grid View')

    def am_i_here(self):
        return match_page('All Configuration Management Providers')


@navigator.register(ConfigManager, 'Add')
class MgrAdd(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn('Add a new Provider')


@navigator.register(ConfigManager, 'Edit')
class MgrEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.quad_name, None).checkbox())
        cfg_btn('Edit Selected item')


@navigator.register(ConfigManager, 'Details')
class MgrDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.quad_name, None))

    def am_i_here(self):
        return any((match_page(summary='Configuration Profiles under Red Hat Satellite '
                                       'Provider "{} Configuration Manager"'.format(self.obj.name)),
                    match_page(summary='Inventory Groups under Ansible Tower Provider'
                                       ' "{} Configuration Manager"'.format(self.obj.name))))


@navigator.register(ConfigManager, 'EditFromDetails')
class MgrEditFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn('Edit this Provider')


# todo: not sure whether this works or not. it seems it wasn't used for a long time
@navigator.register(ConfigProfile, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('manager', 'Details')

    def step(self):
        tb.select('List View'),
        page.list_table_config_profiles.click_cell('Description', self.obj.name)


@navigator.register(ConfigSystem, 'All')
class SysAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Configuration', 'Configuration Management')(None)

    def resetter(self):
        accordion.tree('Configured Systems', 'All Configured Systems')
        tb.select('Grid View')

    def am_i_here(self):
        return match_page(summary='All Configured Systems')


@navigator.register(ConfigSystem, 'Provision')
class SysProvision(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, None))
        cfg_btn('Provision Configured Systems')


@navigator.register(ConfigSystem, 'EditTags')
class SysEditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, None))
        cfg_btn('Edit Tags')
