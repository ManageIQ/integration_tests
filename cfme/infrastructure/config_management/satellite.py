import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import View

from cfme.infrastructure.config_management import ConfigManagementCollectionView
from cfme.infrastructure.config_management import ConfigManagementEntities
from cfme.infrastructure.config_management import ConfigManagementSideBar
from cfme.infrastructure.config_management import ConfigManagementToolbar
from cfme.infrastructure.config_management import ConfigManager
from cfme.infrastructure.config_management import ConfigManagersCollection
from cfme.infrastructure.config_management.config_profiles import ConfigProfilesCollection
from cfme.infrastructure.config_management.config_systems.satellite import SatelliteSystemsCollection  # noqa
from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.version import LATEST
from cfme.utils.version import LOWEST
from cfme.utils.version import VersionPicker
from widgetastic_manageiq import Search


class SatelliteProvidersAllView(ConfigManagementCollectionView):
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


class SatelliteSystemsAllView(SatelliteProvidersAllView):
    """The config system view has a different title"""

    @property
    def is_displayed(self):
        title_text = 'All Configured Systems'
        return (
            self.in_config and
            self.entities.title.text == title_text
        )


@attr.s
class SatelliteProvider(ConfigManager):
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
    type = VersionPicker({
        LOWEST: 'Red Hat Satellite',
        LATEST: 'Foreman'
    })

    ssl = attr.ib(default=None)

    _collections = {
        "config_profiles": ConfigProfilesCollection
    }

    @property
    def ui_name(self):
        """Return the name used in the UI"""
        return '{} Configuration Manager'.format(self.name)

    @classmethod
    def from_config(cls, key):
        """Returns 'ConfigManager' object loaded from yamls, based on its key"""
        data = conf.cfme_data.configuration_managers[key]
        creds = conf.credentials[data['credentials']]
        return cls.appliance.collections.config_managers.instantiate(
            cls,
            name=data['name'],
            url=data['url'],
            ssl=data['ssl'],
            credentials=cls.Credential(
                principal=creds['username'], secret=creds['password']),
            key=key
        )


class SatelliteProvidersCollection(ConfigManagersCollection):
    ENTITY = SatelliteProvider


@navigator.register(SatelliteProvidersCollection, 'All')
class MgrAll(CFMENavigateStep):
    VIEW = SatelliteProvidersAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Configuration', 'Management')
        self.view.sidebar.providers.tree.click_path('All Configuration Manager Providers')


@navigator.register(SatelliteSystemsCollection, 'All')
class SysAll(CFMENavigateStep):
    VIEW = SatelliteSystemsAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Configuration', 'Management')
        self.view.sidebar.configured_systems.tree.click_path("All Configured Systems")
