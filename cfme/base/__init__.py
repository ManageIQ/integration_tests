import attr
import importscan

import sentaku

from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.pretty import Pretty


@attr.s
class Server(BaseEntity, sentaku.modeling.ElementMixin):
    name = attr.ib()
    sid = attr.ib(default=1)
    _zone = attr.ib(init=False, default=None)

    address = sentaku.ContextualMethod()
    login = sentaku.ContextualMethod()
    login_admin = sentaku.ContextualMethod()
    logout = sentaku.ContextualMethod()
    update_password = sentaku.ContextualMethod()
    logged_in = sentaku.ContextualMethod()
    current_full_name = sentaku.ContextualMethod()
    current_username = sentaku.ContextualMethod()

    zone = sentaku.ContextualProperty()
    slave_servers = sentaku.ContextualProperty()

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

    @property
    def collect_logs(self):
        from cfme.configure.configuration.diagnostics_settings import ServerCollectLog
        return ServerCollectLog(self.appliance)


@attr.s
class ServerCollection(BaseCollection, sentaku.modeling.ElementMixin):
    ENTITY = Server

    all = sentaku.ContextualMethod()
    get_master = sentaku.ContextualMethod()


@attr.s
class Zone(Pretty, BaseEntity, sentaku.modeling.ElementMixin):
    """ Configure/Configuration/Region/Zones functionality

    Create/Read/Update/Delete functionality.
    """
    pretty_attrs = ['name', 'description', 'smartproxy_ip', 'ntp_servers', 'max_scans', 'user']

    exists = sentaku.ContextualProperty()
    update = sentaku.ContextualMethod()
    delete = sentaku.ContextualMethod()
    region = sentaku.ContextualProperty()

    name = attr.ib(default="default")
    description = attr.ib(default="Default Zone")
    id = attr.ib(default=None)
    smartproxy_ip = attr.ib(default=None)
    ntp_servers = attr.ib(default=None)
    max_scans = attr.ib(default=None)
    user = attr.ib(default=None)
    _region = attr.ib(init=False, default=None)

    _collections = {'servers': ServerCollection}

    @property
    def collect_logs(self):
        from cfme.configure.configuration.diagnostics_settings import ZoneCollectLog
        return ZoneCollectLog(self.appliance)


@attr.s
class ZoneCollection(BaseCollection, sentaku.modeling.ElementMixin):

    ENTITY = Zone

    region = attr.ib(default=None)

    create = sentaku.ContextualMethod()
    all = sentaku.ContextualMethod()


@attr.s
class Region(BaseEntity, sentaku.modeling.ElementMixin):
    number = attr.ib(default=0)

    _collections = {'zones': ZoneCollection}

    @property
    def settings_string(self):
        return "{} Region: Region {} [{}]".format(
            self.appliance.product_name, self.number, self.number)

    @property
    def replication(self):
        from cfme.configure.configuration.region_settings import Replication
        replication = Replication(self.appliance)
        return replication


@attr.s
class RegionCollection(BaseCollection, sentaku.modeling.ElementMixin):
    all = sentaku.ContextualMethod()

    ENTITY = Region


from . import ui, ssui, rest  # NOQA last for import cycles
importscan.scan(ui)
importscan.scan(ssui)
importscan.scan(rest)
