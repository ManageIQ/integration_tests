"""
Model of Configuration Management in CFME
"""

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View, Text
from widgetastic_manageiq import (ManageIQTree, SummaryTable, ItemsToolBarViewSelector,
                                  BaseEntitiesView)
from widgetastic_patternfly import (Dropdown, Accordion, FlashMessages,
                                    Button, Input, Tab)

from cfme.base.login import BaseLoggedInPage
from cfme.base.credential import Credential as BaseCredential
from utils import version, conf
from utils.appliance import NavigatableMixin
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.log import logger
from utils.pretty import Pretty
from utils.update import Updateable
from utils.wait import wait_for


class ConfigManagementToolbar(View):
    reload = Button('Reload current display')
    configuration = Dropdown(text='Configuration')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ConfigManagementSidebar(View):
    @View.nested
    class Providers(Accordion):
        # noqa
        ACCORDION_NAME = "Providers"
        tree = ManageIQTree()

    @View.nested
    class ConfSystems(Accordion):
        # noqa
        ACCORDION_NAME = "Configured Systems"
        tree = ManageIQTree()


class ConfigManagementEntities(BaseEntitiesView):
    """
    represents central view where all QuadIcons, etc are displayed
    """
    pass


class ConfigManagementView(BaseLoggedInPage):
    """
    represents whole All Config management page
    """
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    toolbar = View.nested(ConfigManagementToolbar)
    sidebar = View.nested(ConfigManagementSidebar)
    including_entities = View.include(ConfigManagementEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Configuration', 'Management'] and
                self.entities.title.text == 'All Configuration Management Providers')


class ConfigAddProviderForm(View):
    name = Input('name')
    url = Input('url')
    verify_cert = Input('verify_ssl')

    username = Input('log_userid')
    password = Input('log_password')
    confirm_password = Input('log_password')
    validate = Button('Validate')

    add = Button('Add')
    cancel = Button('Cancel')


class ConfigManagementAddProviderView(BaseLoggedInPage):
    form = View.nested(ConfigAddProviderForm)

    @property
    def is_displayed(self):
        return self.entities.title.text == 'Add a new Provider'


class ConfigManagementEditProviderForm(ConfigAddProviderForm):
    change_password = Text('Change stored password')
    save = Button('Save')
    reset = Button('Reset')


class ConfigManagementEditProviderView(BaseLoggedInPage):
    form = View.nested(ConfigManagementEditProviderForm)

    @property
    def is_displayed(self):
        return self.entities.title.text == 'Edit Provider'


class ConfigManagementProviderDetailView(BaseLoggedInPage):
    toolbar = View.nested(ConfigManagementToolbar)
    sidebar = View.nested(ConfigManagementSidebar)
    including_entities = View.include(ConfigManagementEntities, use_parent=True)

    @property
    def is_displayed(self):
        msg = 'Configuration Profiles under Red Hat Satellite Provider'
        "\"{} Configuration Manager\"".format(self.obj.name)

        return self.entities.title.text == msg


class ConfigManagementConfProfileToolbarView(View):
    lifecycle = Dropdown()
    policy = Dropdown()
    download = Dropdown()


class ConfigManagementConfProfileView(BaseLoggedInPage):
    toolbar = View.nested(ConfigManagementConfProfileToolbarView)
    sidebar = View.nested(ConfigManagementSidebar)
    including_entities = View.include(ConfigManagementEntities, use_parent=True)

    @View.nested
    class Tabs(View):
        # noqa

        @View.nested
        class Summary(Tab):
            TAB_NAME = 'Summary'

        @View.nested
        class ConfiguredSystem(Tab):
            TAB_NAME = 'Configured Systems'

    @property
    def is_displayed(self):
        return (
            self.entities.title == 'Configured Systems under Configuration Profile "{}"'.format(
                self.obj.name)
        )


class ConfiguredSystems(View):
    toolbar = View.nested(ConfigManagementConfProfileToolbarView)
    sidebar = View.nested(ConfigManagementSidebar)
    properties = SummaryTable(title='Properties')
    enviroment = SummaryTable(title='Environment')
    os = SummaryTable(title='Operating System')
    tenancy = SummaryTable(title='Tenancy')
    smart_management = SummaryTable(title='Smart Management')


class ConfProfileSummary(View):
    properties = SummaryTable(title='Properties')
    env = SummaryTable(title='Enviroment')
    os = SummaryTable(title='Operating System')
    tenancy = SummaryTable(title='Tenancy')


class ConfigManagementCollection(NavigatableMixin):
    "Collection class for Configuration Management"

    def __init__(self, appliance):
        self.appliance = appliance

    def instantiate(self, name, url=None, ssl=None, credentials=None):
        return ConfigManagementProvider(name, url, ssl, credentials)

    def create(self, name, url, ssl, credentials):
        view = navigate_to(self, 'Add')
        view.form.fill({
            'name': name,
            'url': url,
            'username': credentials['username'],
            'password': credentials['password'],
            'confirm_password': credentials['password']
        })
        view.validate.click()
        view.add.click()
        return self.instantiate(name, url, ssl, credentials)

    def delete(self, *providers):
        providers = list(providers)
        view = navigate_to(self, 'All')
        for provider in providers:
            view.entities.get_entity(provider.name).check()
        view.toolbar.configuration.item_select('Remove selected items')

    def refresh_relationship(self, *providers):
        providers = list(providers)
        view = navigate_to(self, 'All')
        for provider in providers:
            view.entities.get_entity(provider.name).check()
        view.toolbar.configuration.item_select('Refresh Relationship and Power states',
                                               handle_alert=True)


class ConfigManagementConfProfile(object):
    "Conf profile under a Configuration Manager"

    def __init__(self, name, provider):
        self.name = name
        self.provider = provider


class ConfigManagementProvider(NavigatableMixin):
    """
    Base class
    """

    def __init__(self, name, url=None, ssl=None, credentials=None):
        self.name = name
        self.url = url
        self.ssl = ssl
        self.credentials = credentials

    def get_confprofiles(self):
        view = navigate_to(self, 'Details')
        profiles = view.entities.get_all()
        if profiles is not None:
            return [ConfigManagementConfProfile(profile.name, self) for profile in profiles]
        else:
            return list()

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


@navigator.register(ConfigManagementCollection, 'All')
class ConfigManagementAll(CFMENavigateStep):
    VIEW = ConfigManagementView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Configuration', 'Management')

    def resetter(self, *args, **kwargs):
        self.view.sidebar.providers.tree.root_item.click()


@navigator.register(ConfigManagementCollection, 'Add')
class ConfigManagerAddProvider(CFMENavigateStep):
    VIEW = ConfigManagementAddProviderView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Provider')


@navigator.register(ConfigManagementProvider, 'Edit')
class ConfigManagerEditProvider(CFMENavigateStep):
    VIEW = ConfigManagementEditProviderView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit Selected item')


@navigator.register(ConfigManagementProvider, 'Details')
class ConfigManagementProviderDetails(CFMENavigateStep):
    VIEW = ConfigManagementProviderDetailView
    prerequisite = NavigateToAttribute(ConfigManagementCollection, 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(self.name).click()

    def resetter(self, *args, **kwargs):
        self.toolbar.view_selector.grid_button.click()


@navigator.register(ConfigManagementProvider, 'EditFromDetails')
class MgrEditFromDetails(CFMENavigateStep):
    VIEW = ConfigManagementEditProviderView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Provider')


@navigator.register(ConfigManagementConfProfile, 'Details')
class Details(CFMENavigateStep):
    VIEW = ConfigManagementConfProfileView
    prerequisite = NavigateToAttribute('provider', 'Details')

    def step(self):
        self.prerequisite_view.entities.get_entity(self.obj.name).click()


def get_config_manager_from_config(cfg_mgr_key):
    cfg_mgr = conf.cfme_data.get('configuration_managers', {})[cfg_mgr_key]
    if cfg_mgr['type'] == 'satellite' or cfg_mgr['type'] == 'ansible':
        return ConfigManagementProvider.load_from_yaml(cfg_mgr_key)
    else:
        raise Exception("Unknown configuration manager key")
