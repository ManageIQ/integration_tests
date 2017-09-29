# -*- coding: utf-8 -*-
from cached_property import cached_property
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import Checkbox, TextInput, Text, View
from widgetastic_manageiq import (
    Accordion, BaseEntitiesView, Button, ItemsToolBarViewSelector, ManageIQTree, SummaryTable,
    Table)
from widgetastic_patternfly import BootstrapSelect, Dropdown, FlashMessages, Tab

from cfme.base.credential import Credential as BaseCredential
from cfme.base.login import BaseLoggedInPage
from cfme.common import WidgetasticTaggable, TagPageView
from cfme.configure.configuration.region_settings import Category, Tag
from cfme.utils import version, conf
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for


class ConfigManagementToolbar(View):
    """Toolbar"""
    refresh = Button(title='Reload current display')
    configuration = Dropdown('Configuration')
    lifecycle = Dropdown('Lifecycle')
    policy = Dropdown('Policy')
    download = Dropdown(title='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ConfigManagementDetailsToolbar(View):
    """Toolbar on the details page"""
    history = Dropdown(title='History')
    refresh = Button(title='Reload current display')
    lifecycle = Dropdown('Lifecycle')
    policy = Dropdown('Policy')
    download = Button(title='Download summary in PDF format')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ConfigManagementSideBar(View):
    """Side bar"""
    @View.nested
    class providers(Accordion):             # noqa
        ACCORDION_NAME = 'Providers'
        tree = ManageIQTree()

    @View.nested
    class configured_systems(Accordion):    # noqa
        ACCORDION_NAME = 'Configured Systems'
        tree = ManageIQTree()

    @View.nested
    class job_templates(Accordion):         # noqa
        ACCORDION_NAME = 'Job Templates'
        tree = ManageIQTree()


class ConfigManagementEntities(BaseEntitiesView):
    """The entities on the page"""
    table = Table('//div[@id="main_div"]//div[@id="list_grid"]/table')


class ConfigManagementProfileEntities(BaseEntitiesView):
    """Entities view for the detail page"""
    @View.nested
    class summary(Tab):                     # noqa
        TAB_NAME = 'Summary'

        properties = SummaryTable(title='Properties')
        environment = SummaryTable(title='Environment')
        operating_system = SummaryTable(title='Operating System')
        tenancy = SummaryTable(title='Tenancy')
        smart_management = SummaryTable(title='Smart Management')

    @View.nested
    class configured_systems(Tab):          # noqa
        TAB_NAME = 'Configured Systems'
        table = Table('//div[@id="main_div"]//div[@id="list_grid"]/table')


class ConfigManagementAddForm(View):
    """Form to add a provider"""
    name = TextInput('name')
    provider_type = BootstrapSelect('provider_type')
    zone = TextInput('zone')
    url = TextInput('url')
    ssl = Checkbox('verify_ssl')

    username = TextInput('log_userid')
    password = TextInput('log_password')
    confirm_password = TextInput('log_verify')

    validate = Button('Validate')


class ConfigManagementEditForm(View):
    """Form to add a provider"""
    name = TextInput('name')
    provider_type = BootstrapSelect('provider_type')
    zone = TextInput('zone')
    url = TextInput('url')
    ssl = Checkbox('verify_ssl')

    username = TextInput('log_userid')
    password = TextInput('log_password')

    validate = Button('Validate')


class ConfigManagementAddEntities(View):
    """The entities on the add page"""
    title = Text('//div[@id="main-content"]//h1')
    form = View.nested(ConfigManagementAddForm)
    add = Button('Add')
    cancel = Button('Cancel')

    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class ConfigManagementEditEntities(View):
    """The entities on the edit page"""
    title = Text('//div[@id="main-content"]//h1')
    form = View.nested(ConfigManagementEditForm)
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class ConfigManagementView(BaseLoggedInPage):
    """The base page for both the all and details page"""

    @property
    def in_config(self):
        """Determine if we're in the config section"""
        if (self.context['object'].appliance.version >= '5.8' and
                self.context['object'].type == 'Ansible Tower'):
            nav_chain = ['Automation', 'Ansible', 'Ansible Tower']
        else:
            nav_chain = ['Configuration', 'Management']
        return self.logged_in_as_current_user and self.navigation.currently_selected == nav_chain


class ConfigManagementAllView(ConfigManagementView):
    """The main list view"""
    toolbar = View.nested(ConfigManagementToolbar)
    sidebar = View.nested(ConfigManagementSideBar)
    including_entities = View.include(ConfigManagementEntities, use_parent=True)

    @property
    def is_displayed(self):
        """Is this view being displayed?"""
        if self.obj.appliance.version >= '5.8' and self.obj.type == 'Ansible Tower':
            title_text = 'All Ansible Tower Providers'
        else:
            title_text = 'All Configuration Manager Providers'
        return self.in_config and self.entities.title.text == title_text


class ConfigManagementDetailsView(ConfigManagementView):
    """The details page"""
    toolbar = View.nested(ConfigManagementToolbar)
    sidebar = View.nested(ConfigManagementSideBar)
    including_entities = View.include(ConfigManagementEntities, use_parent=True)

    @property
    def is_displayed(self):
        """Is this view being displayed?"""
        titles = [t.format(self.obj.name) for t in [
            'Configuration Profiles under Red Hat Satellite Provider "{} Configuration Manager"',
            'Inventory Groups under Ansible Tower Provider "{} Configuration Manager"'
        ]]
        return self.in_config and self.entities.title.text in titles


class ConfigManagementProfileView(ConfigManagementView):
    """The profile page"""
    toolbar = View.nested(ConfigManagementDetailsToolbar)
    sidebar = View.nested(ConfigManagementSideBar)
    entities = View.nested(ConfigManagementProfileEntities)

    @property
    def is_displayed(self):
        """Is this view being displayed?"""
        title = 'Configured System ({}) "{}"'.format(self.obj.type, self.obj.name)
        return self.in_config and self.entities.title.text == title


class ConfigManagementAddView(ConfigManagementView):
    """The add page"""
    sidebar = View.nested(ConfigManagementSideBar)
    entities = View.nested(ConfigManagementAddEntities)

    @property
    def is_displayed(self):
        """Is this view being displayed?"""
        return False


class ConfigManagementEditView(ConfigManagementView):
    """The edit page"""
    sidebar = View.nested(ConfigManagementSideBar)
    entities = View.nested(ConfigManagementEditEntities)

    @property
    def is_displayed(self):
        """Is this view being displayed?"""
        return False


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

    class Credential(BaseCredential, Updateable):
        pass

    @property
    def ui_name(self):
        """Return the name used in the UI"""
        return '{} Configuration Manager'.format(self.name)

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
        form_dict = self.__dict__
        form_dict.update(self.credentials.view_value_mapping)
        if self.appliance.version < '5.8':
            form_dict['provider_type'] = self.type
        view = navigate_to(self, 'Add')
        view.entities.form.fill(form_dict)
        if validate_credentials:
            view.entities.form.validate.click()
            view.entities.flash.assert_success_message('Credential validation was successful')
        if cancel:
            view.entities.cancel.click()
            view.entities.flash.assert_success_message('Add of Provider was cancelled by the user')
        else:
            view.entities.add.click()
            success_message = '{} Provider "{}" was added'.format(self.type, self.name)
            view.entities.flash.assert_success_message(success_message)
            view.entities.flash.assert_success_message(self._refresh_flash_msg)
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
        view = navigate_to(self, 'Edit')
        view.entities.form.fill(updates)
        if validate_credentials:
            view.entities.form.validate.click()
            view.entities.flash.assert_success_message('Credential validation was successful')
        if cancel:
            view.entities.cancel.click()
            view.entities.flash.assert_success_message('Edit of Provider was cancelled by the user')
        else:
            view.entities.save.click()
            view.entities.flash.assert_success_message(
                '{} Provider "{}" was updated'.format(self.type, updates['name'] or self.name))
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
        view = navigate_to(self, 'All')
        view.toolbar.view_selector.select('List View')
        row = view.entities.paginator.find_row_on_pages(view.entities.elements,
                                                        provider_name=self.ui_name)
        row[0].check()
        view.toolbar.configuration.item_select('Remove selected items', handle_alert=not cancel)
        if not cancel:
            view.entities.flash.assert_success_message('Delete initiated for 1 Provider')
            if wait_deleted:
                wait_for(func=lambda: self.exists, fail_condition=True, delay=15, num_sec=60)

    @property
    def _refresh_flash_msg(self):
        return version.pick({'5.7': 'Refresh Provider initiated for 1 provider ({})'.
                                    format(self.type),
                             '5.8': 'Refresh Provider initiated for 1 provider'})

    @property
    def exists(self):
        """Returns whether the manager exists in the UI or not"""
        view = navigate_to(self, 'All')
        view.toolbar.view_selector.select('List View')
        try:
            view.entities.paginator.find_row_on_pages(view.entities.elements,
                                                      provider_name=self.ui_name)
            return True
        except NoSuchElementException:
            pass
        return False

    def refresh_relationships(self, cancel=False):
        """Refreshes relationships and power states of this manager"""
        view = navigate_to(self, 'All')
        view.toolbar.view_selector.select('List View')
        row = view.entities.paginator.find_row_on_pages(view.entities.elements,
                                                        provider_name=self.ui_name)
        row[0].check()
        if view.toolbar.configuration.item_enabled('Refresh Relationships and Power states'):
            view.toolbar.configuration.item_select('Refresh Relationships and Power states',
                                                   handle_alert=not cancel)
        if not cancel:
            view.entities.flash.assert_success_message(self._refresh_flash_msg)

    @property
    def config_profiles(self):
        """Returns 'ConfigProfile' configuration profiles (hostgroups) available on this manager"""
        view = navigate_to(self, 'Details')
        # TODO - remove it later.Workaround for BZ 1452425
        view.toolbar.view_selector.select('List View')
        view.toolbar.refresh.click()
        wait_for(lambda: view.entities.elements.is_displayed, fail_func=view.toolbar.refresh.click,
                 handle_exception=True, num_sec=60, delay=5)
        config_profiles = []
        for row in view.entities.elements:
            if self.type == 'Ansible Tower':
                name = row.name.text
            else:
                name = row.description.text
            if 'unassigned' in name.lower():
                continue
            config_profiles.append(ConfigProfile(name=name, manager=self))
        return config_profiles

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
        if version.current_version() >= '5.8' and self.type == 'Ansible Tower':
            return '{} Automation Manager'.format(self.name)
        else:
            return '{} Configuration Manager'.format(self.name)


def get_config_manager_from_config(cfg_mgr_key):
    cfg_mgr = conf.cfme_data.get('configuration_managers', {})[cfg_mgr_key]
    if cfg_mgr['type'] == 'satellite':
        return Satellite.load_from_yaml(cfg_mgr_key)
    elif cfg_mgr['type'] == 'ansible':
        return AnsibleTower.load_from_yaml(cfg_mgr_key)
    else:
        raise Exception("Unknown configuration manager key")


class ConfigProfile(Pretty, Navigatable):
    """Configuration profile object (foreman-side hostgroup)

    Args:
        name: Name of the profile
        manager: ConfigManager object which this profile is bound to
    """
    pretty_attrs = ['name', 'manager']

    def __init__(self, name, manager, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.manager = manager

    @property
    def systems(self):
        """Returns 'ConfigSystem' objects that are active under this profile"""
        view = navigate_to(self, 'Details')
        view.toolbar.view_selector.select('List View')

        # Unassigned config profile has no tabstrip
        if 'unassigned' not in self.name.lower():
            view.entities.configured_systems.click()

        if view.entities.configured_systems.table.is_displayed:
            return [ConfigSystem(row.hostname.text, self)
                    for row in view.entities.configured_systems.table]
        return list()


class ConfigSystem(Pretty, Navigatable, WidgetasticTaggable):
    """The tags pages of the config system"""
    pretty_attrs = ['name', 'manager_key']

    def __init__(self, name, profile, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.profile = profile

    def get_tags(self, tenant="My Company Tags"):
        """Overridden get_tags method to deal with the fact that configured systems don't have a
        details view."""
        view = navigate_to(self, 'EditTags')
        return [Tag(category=Category(display_name=r.category.text.replace('*', '').strip()),
                    display_name=r.assigned_value.text.strip())
                for r in view.form.tags]


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
    VIEW = ConfigManagementAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        if self.obj.appliance.version < '5.8' or self.obj.type != 'Ansible Tower':
            self.prerequisite_view.navigation.select('Configuration', 'Management')
        else:
            self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Explorer')

    def resetter(self):
        if self.obj.appliance.version >= '5.8' and self.obj.type == 'Ansible Tower':
            self.view.sidebar.providers.tree.click_path('All Ansible Tower Providers')
        else:
            self.view.sidebar.providers.tree.click_path('All Configuration Manager Providers')


@navigator.register(ConfigManager, 'Add')
class MgrAdd(CFMENavigateStep):
    VIEW = ConfigManagementAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Provider')


@navigator.register(ConfigManager, 'Edit')
class MgrEdit(CFMENavigateStep):
    VIEW = ConfigManagementEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        row = self.prerequisite_view.entities.paginator.find_row_on_pages(
            self.prerequisite_view.entities.elements, provider_name=self.obj.ui_name)
        row.click()
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Provider')


@navigator.register(ConfigManager, 'Details')
class MgrDetails(CFMENavigateStep):
    VIEW = ConfigManagementDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        row = self.prerequisite_view.entities.paginator.find_row_on_pages(
            self.prerequisite_view.entities.elements, provider_name=self.obj.ui_name)
        row.click()


@navigator.register(ConfigManager, 'EditFromDetails')
class MgrEditFromDetails(CFMENavigateStep):
    VIEW = ConfigManagementEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Provider')


@navigator.register(ConfigProfile, 'Details')
class Details(CFMENavigateStep):
    VIEW = ConfigManagementProfileView
    prerequisite = NavigateToAttribute('manager', 'Details')

    def step(self):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        row = self.prerequisite_view.entities.paginator.find_row_on_pages(
            self.prerequisite_view.entities.elements, description=self.obj.name)
        row.click()


@navigator.register(ConfigSystem, 'All')
class SysAll(CFMENavigateStep):
    VIEW = ConfigManagementAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Configuration', 'Management')

    def resetter(self):
        self.view.sidebar.configured_systems.open()
        self.view.sidebar.configured_systems.tree.click_path('All Configured Systems')


@navigator.register(ConfigSystem, 'EditTags')
class SysEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        row = self.prerequisite_view.entities.paginator.find_row_on_pages(
            self.prerequisite_view.entities.elements, hostname=self.obj.name)
        row[0].check()
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
