import attr
from manageiq_client.api import APIException
from manageiq_client.api import Entity as RestEntity
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from navmazing import NavigationDestinationNotFound
from widgetastic.widget import Checkbox
from widgetastic.widget import Text
from widgetastic.widget import TextInput
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Dropdown

from cfme.base.credential import Credential as BaseCredential
from cfme.common import BaseLoggedInPage
from cfme.common import TagPageView
from cfme.common.provider import BaseProvider
from cfme.exceptions import displayed_not_implemented
from cfme.infrastructure.config_management.config_profiles import ConfigProfile
from cfme.infrastructure.config_management.config_profiles import ConfigProfilesCollection
from cfme.infrastructure.config_management.config_systems import ConfigSystem
from cfme.modeling.base import BaseCollection
from cfme.utils import ParamClassName
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.rest import assert_response
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import Button
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import Table
from widgetastic_manageiq import WaitTab


class ConfigManagementToolbar(View):
    """Toolbar"""
    reload = Button(title='Refresh this page')
    configuration = Dropdown('Configuration')
    lifecycle = Dropdown('Lifecycle')
    policy = Dropdown('Policy')
    download = Dropdown(title='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ConfigManagementDetailsToolbar(View):
    """Toolbar on the details page"""
    history = Dropdown(title='History')
    refresh = Button(title='Refresh this page')
    lifecycle = Dropdown('Lifecycle')
    policy = Dropdown('Policy')
    download = Button(title='Print or export summary')
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
    table = Table("//div[@id='gtl_div']//table")
    add_button = Button('Add a Provider')


class ConfigManagementAddForm(View):
    """Form to add a provider"""
    name = TextInput('name')
    provider_type = BootstrapSelect('provider_type')
    zone = TextInput('zone')
    url = TextInput('url')
    ssl = Checkbox('verify_ssl')

    username = TextInput('default_userid')
    password = TextInput('default_password')
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


class ConfigManagementEditEntities(View):
    """The entities on the edit page"""
    title = Text('//div[@id="main-content"]//h1')
    form = View.nested(ConfigManagementEditForm)
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


class ConfigManagementCollectionView(BaseLoggedInPage):
    """ Base page for ALL """

    @property
    def in_config(self):
        """Determine if we're in the config section"""
        object_type = getattr(self.context['object'], 'type_name', None)
        if object_type == 'ansible_tower':
            nav_chain = ['Automation', 'Ansible Tower', 'Explorer']
        elif object_type == "satellite":
            nav_chain = ['Configuration', 'Management']
        else:
            nav_chain = []
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav_chain
        )


class ConfigManagementView(BaseLoggedInPage):
    """The base page for the details page"""

    @property
    def in_config(self):
        """Determine if we're in the config section"""
        object_type = getattr(self.context['object'], 'type_name', None)
        if object_type == 'ansible_tower':
            nav_chain = ['Automation', 'Ansible Tower', 'Explorer']
        elif object_type == "satellite":
            nav_chain = ['Configuration', 'Management']
        else:
            nav_chain = []
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav_chain
        )


class ConfigManagementDetailsView(ConfigManagementView):
    """The details page"""
    toolbar = View.nested(ConfigManagementToolbar)
    sidebar = View.nested(ConfigManagementSideBar)
    including_entities = View.include(ConfigManagementEntities, use_parent=True)

    @property
    def is_displayed(self):
        """Is this view being displayed?"""
        titles = [
            'Configuration Profiles under Red Hat Satellite Provider '  # continued ...
            '"{name} Configuration Manager"',
            'Inventory Groups under Ansible Tower Provider "{name} Automation Manager"'
        ]
        return (
            self.in_config and
            self.entities.title.text in [t.format(name=self.context['object'].name) for t in titles]
        )


class ConfigManagementAddView(ConfigManagementView):
    """The add page"""
    sidebar = View.nested(ConfigManagementSideBar)
    entities = View.nested(ConfigManagementAddEntities)
    is_displayed = displayed_not_implemented


class ConfigManagementEditView(ConfigManagementView):
    """The edit page"""
    sidebar = View.nested(ConfigManagementSideBar)
    entities = View.nested(ConfigManagementEditEntities)
    is_displayed = displayed_not_implemented


class ConfigManagementProfileEntities(BaseEntitiesView):
    """Entities view for the detail page"""
    @View.nested
    class summary(WaitTab):                     # noqa
        TAB_NAME = 'Summary'

        properties = SummaryTable(title='Properties')
        environment = SummaryTable(title='Environment')
        operating_system = SummaryTable(title='Operating System')
        tenancy = SummaryTable(title='Tenancy')
        smart_management = SummaryTable(title='Smart Management')

    @View.nested
    class configured_systems(WaitTab):          # noqa
        TAB_NAME = 'Configured Systems'
        elements = Table('//div[@id="main_div"]//div[@id="list_grid" or @id="gtl_div"]//table')


class ConfigManagerProvidersAllView(ConfigManagementCollectionView):
    """The main list view"""
    toolbar = View.nested(ConfigManagementToolbar)
    sidebar = View.nested(ConfigManagementSideBar)
    search = View.nested(Search)
    including_entities = View.include(ConfigManagementEntities, use_parent=True)

    @property
    def is_displayed(self):
        """Is this view being displayed?"""
        title_text = 'All Configuration Management Providers'
        return (
            self.in_config and
            self.entities.title.text == title_text
        )


class ConfigManagementProfileView(ConfigManagementView):
    """The profile page"""
    toolbar = View.nested(ConfigManagementDetailsToolbar)
    sidebar = View.nested(ConfigManagementSideBar)
    including_entities = View.include(ConfigManagementProfileEntities, use_parent=True)

    @property
    def is_displayed(self):
        title = 'Configured Systems under {} "{}"'.format(
            self.context['object'].type,
            self.context['object'].name)
        return self.entities.title.text == title


@attr.s(eq=False)
class ConfigManagerProvider(BaseProvider, Updateable, Pretty):
    """
    This is base class for Configuration manager objects (Red Hat Satellite, Foreman, Ansible Tower)

    Args:
        name: Name of the config. manager
        url: URL, hostname or IP of the config. manager
        credentials: Credentials to access the config. manager
        key: Key to access the cfme_data yaml data (same as `name` if not specified)

    Usage:
        Use Satellite or AnsibleTower classes instead.
    """

    pretty_attr = ['name', 'key']
    _param_name = ParamClassName('name')
    category = "config_manager"
    refresh_flash_msg = 'Refresh Provider initiated for 1 provider'
    name = attr.ib(default=None)
    url = attr.ib(default=None)
    credentials = attr.ib(default=None)
    key = attr.ib(default=None)
    ui_type = None

    _collections = {"config_profiles": ConfigProfilesCollection}

    class Credential(BaseCredential, Updateable):
        pass

    @property
    def exists(self):
        """ Returns ``True`` if a provider of the same name exists on the appliance
            This overwrite of BaseProvider exists is necessary because MIQ appends
            Configuration Manager to the provider name
        """
        for name in self.appliance.managed_provider_names:
            if self.name in name:
                return True
        return False

    def create(self, cancel=False, validate_credentials=True, validate=True, force=False, **kwargs):
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
                set(config_profiles_names), set(self.data['config_profiles'])
            )
            # Just validate any profiles from yaml are in UI - not all are displayed
            return any(
                [cp in config_profiles_names for cp in self.data['config_profiles']])

        if not force and self.exists:
            return

        form_dict = self.__dict__
        form_dict.update(self.credentials.view_value_mapping)

        view = navigate_to(self, 'Add')
        view.entities.form.fill(form_dict)
        if validate_credentials:
            view.entities.form.validate.click()
            view.flash.assert_success_message('Credential validation was successful')
        if cancel:
            view.entities.cancel.click()
            view.flash.assert_success_message('Add of Provider was cancelled by the user')
        else:
            view.entities.add.wait_displayed('2s')
            view.entities.add.click()
            success_message = f'{self.ui_type} Provider "{self.name}" was added'
            view.flash.assert_success_message(success_message)
            view.flash.assert_success_message(self.refresh_flash_msg)
            if validate:
                try:
                    self.data['config_profiles']
                except KeyError as e:
                    logger.exception(e)
                    raise

                wait_for(
                    config_profiles_loaded,
                    fail_func=self.refresh_relationships,
                    handle_exception=True,
                    num_sec=180, delay=30
                )

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
            view.flash.assert_success_message('Credential validation was successful')
        if cancel or view.entities.save.disabled:
            view.entities.cancel.click()
            view.flash.assert_success_message('Edit of Provider was cancelled by the user')
        else:
            view.entities.save.click()
            view.flash.assert_success_message(
                '{} Provider "{}" was updated'.format(self.ui_type,
                    updates.get('name') or self.name))
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
        view = navigate_to(self, 'AllOfType')
        provider_entity = view.entities.get_entities_by_keys(provider_name=self.ui_name)
        provider_entity[0].ensure_checked()
        remove_item = 'Remove selected items from Inventory'
        view.toolbar.configuration.item_select(remove_item, handle_alert=not cancel)
        if not cancel:
            view.flash.assert_success_message('Delete initiated for 1 Provider')
            if wait_deleted:
                wait_for(
                    # check the provider is not listed in all providers anymore
                    func=lambda: not view.entities.get_entities_by_keys(
                        provider_name=self.ui_name
                    ), delay=15, fail_func=view.toolbar.refresh.click, num_sec=5 * 60
                )
                # check the provider is indeed deleted
                assert not self.exists

    @property
    def rest_api_entity(self):
        """Returns the rest entity of config manager provider"""
        # Since config manager provider is slightly different from other normal providers,
        # we cannot obtain it's rest entity the normal way, instead, we use Entity class
        # of manageiq_client library to instantiate the rest entity.
        provider_id = self.appliance.rest_api.collections.providers.get(
            name=self.ui_name
        ).provider_id

        return RestEntity(self.appliance.rest_api.collections.providers, data={
            "href": self.appliance.url_path(
                f"/api/providers/{provider_id}?provider_class=provider"
            )
        })

    # TODO: implement this via Sentaku
    def create_rest(self, check_existing=False, validate_inventory=False):
        """Create the config manager in CFME using REST"""
        if check_existing and self.exists:
            return False

        logger.info("Setting up provider via REST: %s", self.key)

        if self.type == "ansible_tower":
            config_type = "AnsibleTower"
        else:
            config_type = "Foreman"

        payload = {
            "type": f"ManageIQ::Providers::{config_type}::Provider",
            "url": self.url,
            "name": self.name,
            "credentials": {
                "userid": self.credentials.view_value_mapping["username"],
                "password": self.credentials.view_value_mapping["password"],
            },
            "verify_ssl": self.ssl,
        }

        try:
            self.appliance.rest_api.post(
                api_endpoint_url=self.appliance.url_path(
                    "/api/providers/?provider_class=provider"
                ),
                **payload
            )
        except APIException as err:
            raise AssertionError(f"Provider wasn't added: {err}")

        response = self.appliance.rest_api.response
        if not response:
            raise AssertionError(
                f"Provider wasn't added, status code {response.status_code}"
            )
        if validate_inventory:
            self.validate(timeout=300)

        assert_response(self.appliance)
        return True

    def refresh_relationships(self, cancel=False):
        """Refreshes relationships and power states of this manager"""
        view = navigate_to(self, 'AllOfType')
        view.toolbar.view_selector.select('List View')
        provider_entity = view.entities.get_entities_by_keys(provider_name=self.ui_name)[0]
        provider_entity.ensure_checked()
        if view.toolbar.configuration.item_enabled('Refresh Relationships and Power states'):
            view.toolbar.configuration.item_select('Refresh Relationships and Power states',
                                                   handle_alert=not cancel)
        if not cancel:
            view.flash.assert_success_message(self.refresh_flash_msg)

    @property
    def config_profiles(self):
        """Returns 'ConfigProfile' configuration profiles (hostgroups) available on this manager"""
        return self.collections.config_profiles.all()

    @property
    def config_systems(self):
        """Returns 'ConfigSystem' configured systems (hosts) available on this manager"""
        systems_per_prof = [prof.config_systems for prof in self.config_profiles]
        return [item for sublist in systems_per_prof for item in sublist]

    @property
    def quad_name(self):
        return self.ui_name


class ConfigManagerProviderCollection(BaseCollection):

    ENTITY = ConfigManagerProvider

    def instantiate(self, prov_class, *args, **kwargs):
        return prov_class.from_collection(self, *args, **kwargs)

    def create(self, *args, **kwargs):
        """ Create/add config manager via UI """
        config_manager = self.instantiate(*args, **kwargs)
        config_manager.create(**kwargs)
        return config_manager


@navigator.register(ConfigManagerProvider, 'Add')
class MgrAdd(CFMENavigateStep):
    VIEW = ConfigManagementAddView
    prerequisite = NavigateToSibling('AllOfType')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Provider')


@navigator.register(ConfigManagerProvider, 'Edit')
class MgrEdit(CFMENavigateStep):
    VIEW = ConfigManagementEditView
    prerequisite = NavigateToSibling('AllOfType')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        row = self.prerequisite_view.entities.paginator.find_row_on_pages(
            self.prerequisite_view.entities.elements, provider_name=self.obj.ui_name)
        row.click()
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Provider')


@navigator.register(ConfigManagerProvider, 'Details')
class MgrDetails(CFMENavigateStep):
    VIEW = ConfigManagementDetailsView
    prerequisite = NavigateToSibling('AllOfType')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        row = self.prerequisite_view.entities.paginator.find_row_on_pages(
            self.prerequisite_view.entities.elements, provider_name=self.obj.ui_name)
        row.click()


@navigator.register(ConfigManagerProvider, 'EditFromDetails')
class MgrEditFromDetails(CFMENavigateStep):
    VIEW = ConfigManagementEditView
    prerequisite = NavigateToSibling('AllOfType')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Provider')


@navigator.register(ConfigSystem, 'EditTags')
class SysEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToAttribute('profile', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        row = self.prerequisite_view.entities.paginator.find_row_on_pages(
            self.prerequisite_view.entities.elements, hostname=self.obj.name)
        row[0].check()
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(ConfigProfile, 'Details')
class Details(CFMENavigateStep):
    VIEW = ConfigManagementProfileView
    prerequisite = NavigateToAttribute('manager', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.entities.paginator.find_row_on_pages(
                self.prerequisite_view.entities.elements, name=self.obj.name
            )
        except NameError:
            row = self.prerequisite_view.entities.paginator.find_row_on_pages(
                self.prerequisite_view.entities.elements, description=self.obj.name
            )

        row.click()


@navigator.register(ConfigManagerProviderCollection, "All")
class ConfigManagerAllPage(CFMENavigateStep):

    def step(self, *args, **kwargs):
        raise NavigationDestinationNotFound(
            "There is no page in MIQ that displays all config managers."
            " Use 'AllOfType' on a config manager provider instance."
        )
