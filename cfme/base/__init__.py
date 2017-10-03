import attr

import sentaku

from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance import Navigatable
from cfme.utils.pretty import Pretty


class Server(Navigatable, sentaku.modeling.ElementMixin):
    def __init__(self, appliance, zone=None, name="EVM", sid=1):
        Navigatable.__init__(self, appliance=appliance)
        self.zone = zone or appliance.server.zone
        self.name = name
        self.sid = sid
        self.zone.servers.append(self)
        self.parent = self.appliance.context

    address = sentaku.ContextualMethod()
    login = sentaku.ContextualMethod()
    login_admin = sentaku.ContextualMethod()
    logout = sentaku.ContextualMethod()
    update_password = sentaku.ContextualMethod()
    logged_in = sentaku.ContextualMethod()
    current_full_name = sentaku.ContextualMethod()
    current_username = sentaku.ContextualMethod()

    @property
    def settings(self):
        from cfme.configure.configuration.server_settings import ServerInformation
        setting = ServerInformation(appliance=self.appliance)
        return setting

    @property
    def authentication(self):
        from cfme.configure.configuration.server_settings import AuthenticationSetting
        auth_settings = AuthenticationSetting(self.appliance)
        return auth_settings


@attr.s
class Zone(Pretty, BaseEntity, sentaku.modeling.ElementMixin):
    """ Configure/Configuration/Region/Zones functionality

    Create/Read/Update/Delete functionality.
    """
    pretty_attrs = ['name', 'description', 'smartproxy_ip', 'ntp_servers', 'max_scans', 'user']

    exists = sentaku.ContextualProperty()
    update = sentaku.ContextualMethod()
    delete = sentaku.ContextualMethod()

    region = attr.ib(default=None)
    name = attr.ib(default="default")
    description = attr.ib(default="Default Zone")
    smartproxy_ip = attr.ib(default=None)
    ntp_servers = attr.ib(default=None)
    max_scans = attr.ib(default=None)
    user = attr.ib(default=None)

    # TODO we need to fix this set() addition
    def __attrs_post_init__(self):
        self.servers = []
        self.region = self.region or self.appliance.server.zone.region
        self.region.zones.append(self)


@attr.s
class ZoneCollection(BaseCollection, sentaku.modeling.ElementMixin):

    ENTITY = Zone

    region = attr.ib(default=None)

    create = sentaku.ContextualMethod()

    def __attrs_post_init__(self):
        self.region = self.region or self.appliance.server.zone.region


class Region(Navigatable, sentaku.modeling.ElementMixin):
    def __init__(self, appliance, number=0):
        self.appliance = appliance
        self.zones = []
        self.number = number
        self.parent = self.appliance.context

    @property
    def settings_string(self):
        return "{} Region: Region {} [{}]".format(
            self.appliance.product_name, self.number, self.number)

from . import ui, ssui  # NOQA last for import cycles
sentaku.register_external_implementations_in(ui, ssui)
