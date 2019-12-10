import attr

from cfme.infrastructure.config_management.config_systems import ConfigSystem
from cfme.infrastructure.config_management.config_systems import ConfigSystemsCollection


@attr.s
class SatelliteSystem(ConfigSystem):
    pass


@attr.s
class SatelliteSystemsCollection(ConfigSystemsCollection):
    ENTITY = SatelliteSystem
