import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import View

from cfme.infrastructure.config_management import ConfigManagementCollectionView
from cfme.infrastructure.config_management import ConfigManagementEntities
from cfme.infrastructure.config_management import ConfigManagementSideBar
from cfme.infrastructure.config_management import ConfigManagementToolbar
from cfme.infrastructure.config_management import ConfigManagerProvider
from cfme.infrastructure.config_management.config_profiles import ConfigProfilesCollection
from cfme.infrastructure.config_management.config_systems import ConfigSystem
from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Search


class AnsibleTowerProvidersAllView(ConfigManagementCollectionView):
    """The main list view"""
    toolbar = View.nested(ConfigManagementToolbar)
    sidebar = View.nested(ConfigManagementSideBar)
    search = View.nested(Search)
    including_entities = View.include(ConfigManagementEntities, use_parent=True)

    @property
    def is_displayed(self):
        title_text = 'All Ansible Tower Providers'
        return (
            self.in_config and
            self.entities.title.text == title_text
        )


class ConfigSystemAllView(AnsibleTowerProvidersAllView):
    """The config system view has a different title"""

    @property
    def is_displayed(self):
        title_text = 'All Ansible Tower Configured Systems'
        return (
            self.in_config and
            self.entities.title.text == title_text
        )


@attr.s(eq=False)
class AnsibleTowerProvider(ConfigManagerProvider):
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
    type_name = 'ansible_tower'
    ui_type = 'Ansible Tower'

    _collections = {
        "config_profiles": ConfigProfilesCollection
    }

    @property
    def ui_name(self):
        """Return the name used in the UI"""
        return '{} Automation Manager'.format(self.name)

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        """Returns 'ConfigManager' object loaded from yamls, based on its key"""
        data = prov_config
        creds = conf.credentials[data['credentials']]
        return cls.appliance.collections.config_managers.instantiate(
            cls,
            name=data['name'],
            url=data['url'],
            credentials=cls.Credential(
                principal=creds['username'], secret=creds['password']),
            key=prov_key
        )


@navigator.register(AnsibleTowerProvider, 'AllOfType')
class MgrAll(CFMENavigateStep):
    VIEW = AnsibleTowerProvidersAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Explorer')
        self.view.sidebar.providers.tree.click_path('All Ansible Tower Providers')

    def resetter(self, *args, **kwargs):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")


@navigator.register(ConfigSystem, 'All')
class SysAll(CFMENavigateStep):
    VIEW = ConfigSystemAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Explorer')
        self.view.sidebar.configured_systems.tree.click_path(
            'All Ansible Tower Configured Systems'
        )
