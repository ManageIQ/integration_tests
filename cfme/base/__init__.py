import sentaku
import attr
from cfme.exceptions import ZoneNotFound

from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigate_to
from utils.pretty import Pretty


@attr.s
class HackyElement(sentaku.Element):
    parent = attr.ib()

    @classmethod
    def from_appliance(cls, appliance, parent=None, **kwargs):
        return cls(
            appliance=appliance,
            parent=parent or appliance.context,
            **kwargs)


@attr.s
class Server(Navigatable, HackyElement):
    zone = attr.ib()
    name = attr.ib(default='EVM')
    sid = attr.ib(default=1)

    @classmethod
    def from_appliance(cls, appliance, zone=None, **kwargs):
        self = super(Server, cls).from_appliance(
            appliance=appliance, zone=zone or appliance.server.zone, **kwargs)
        self.zone.servers.add(self)
        return self


@attr.s
class ZoneCollection(Navigatable, HackyElement):

    create = sentaku.ContextualMethod()

    region = attr.ib()

    @classmethod
    def from_appliance(cls, appliance, region=None, **kwargs):
        region = region or appliance.server.zone.region
        return super(ZoneCollection, cls).from_appliance(appliance, region=region, **kwargs)


@attr.s
class Zone(Pretty, Navigatable, sentaku.Element):
    """ Configure/Configuration/Region/Zones functionality

    Create/Read/Update/Delete functionality.
    """
    pretty_attrs = ['name', 'description', 'smartproxy_ip', 'ntp_servers',
                    'max_scans', 'user']

    exists = sentaku.ContextualProperty()
    update = sentaku.ContextualMethod()
    delete = sentaku.ContextualMethod()

    servers = attr.ib(default=attr.Factory(set))
    region = attr.ib()
    name = attr.ib(default="default")
    description = attr.ib(default="Default Zone")

    smartproxy_ip = attr.ib(default=None)
    ntp_servers = attr.ib(default=None)
    max_scans = attr.ib(default=None)
    user = attr.ib(default=None)

    @classmethod
    def from_appliance(cls, appliance, region=None, **kwargs):
        region = region or appliance.server.zone.region
        self = super(Zone, cls).from_appliance(appliance, region=region, **kwargs)
        self.region.zones.add(self)
        return self


@attr.s
class Region(Navigatable, sentaku.Element):
    zones = attr.ib(default=attr.Factory(set))
    number = attr.ib(default=1)

    @property
    def settings_string(self):
        return "{} Region: Region {} [{}]".format(
            self.appliance.product_name, self.number, self.number)

from . import ui, ssui  # NOQA last for import cycles
sentaku.register_external_implementations_in(ui, ssui)
