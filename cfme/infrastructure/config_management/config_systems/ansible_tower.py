import attr

from cfme.infrastructure.config_management.config_systems import ConfigSystem
from cfme.infrastructure.config_management.config_systems import ConfigSystemsCollection


@attr.s
class AnsibleTowerSystem(ConfigSystem):
    pass


@attr.s
class AnsibleTowerSystemsCollection(ConfigSystemsCollection):
    ENTITY = AnsibleTowerSystem
