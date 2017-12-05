import attr
import importscan
import sentaku

from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.pretty import Pretty


@attr.s
class Server(BaseEntity, sentaku.modeling.ElementMixin):
    name = attr.ib()
    sid = attr.ib(default=1)

    address = sentaku.ContextualMethod()
    login = sentaku.ContextualMethod()
    login_admin = sentaku.ContextualMethod()
    logout = sentaku.ContextualMethod()
    update_password = sentaku.ContextualMethod()
    logged_in = sentaku.ContextualMethod()
    current_full_name = sentaku.ContextualMethod()
    current_username = sentaku.ContextualMethod()

    # zone = sentaku.ContextualProperty()
    # slave_servers = sentaku.ContextualProperty()

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

    @property
    def zone(self):
        server_res = self.appliance.rest_api.collections.servers.find_by(id=self.sid)
        server = server_res[0]
        server.reload(attributes=['zone'])
        zone = server.zone
        zone_obj = self.appliance.collections.zones.instantiate(
            name=zone.name, description=zone.description, id=zone.id
        )
        return zone_obj

    @property
    def slave_servers(self):
        return self.zone.collections.servers.filter({'slave': True}).all()


@attr.s
class ServerCollection(BaseCollection, sentaku.modeling.ElementMixin):

    ENTITY = Server

    # all = sentaku.ContextualMethod()
    # get_master = sentaku.ContextualMethod()

    def all(self):
        server_collection = self.appliance.rest_api.collections.servers
        servers = []
        parent = self.filters.get('parent')
        slave_only = self.filters.get('slave', False)
        for server in server_collection:
            server.reload(attributes=['zone_id'])
            if parent and server.zone_id != parent.id:
                continue
            if slave_only and server.is_master:
                continue
            servers.append(self.instantiate(name=server.name, sid=server.id))
        # TODO: This code needs a refactor once the attributes can be loaded from the collection
        return servers

    def get_master(self):
        server_collection = self.appliance.rest_api.collections.servers
        server = server_collection.find_by(is_master=True)[0]
        return self.instantiate(name=server.name, sid=server.id)


@attr.s
class Zone(Pretty, BaseEntity, sentaku.modeling.ElementMixin):
    """ Configure/Configuration/Region/Zones functionality

    Create/Read/Update/Delete functionality.
    """
    pretty_attrs = ['name', 'description', 'smartproxy_ip', 'ntp_servers', 'max_scans', 'user']

    exists = sentaku.ContextualProperty()
    update = sentaku.ContextualMethod()
    delete = sentaku.ContextualMethod()
    # region = sentaku.ContextualProperty()

    name = attr.ib(default="default")
    description = attr.ib(default="Default Zone")
    id = attr.ib(default=None)
    smartproxy_ip = attr.ib(default=None)
    ntp_servers = attr.ib(default=None)
    max_scans = attr.ib(default=None)
    user = attr.ib(default=None)

    _collections = {'servers': ServerCollection}

    @property
    def collect_logs(self):
        from cfme.configure.configuration.diagnostics_settings import ZoneCollectLog
        return ZoneCollectLog(self.appliance)

    @property
    def region(self):
        zone_res = self.appliance.rest_api.collections.zones.find_by(id=self.id)
        zone = zone_res[0]
        zone.reload(attributes=['region_number'])
        region_obj = self.appliance.collections.regions.instantiate(number=zone.region_number)
        return region_obj


@attr.s
class ZoneCollection(BaseCollection, sentaku.modeling.ElementMixin):

    ENTITY = Zone

    region = attr.ib(default=None)

    create = sentaku.ContextualMethod()
    # all = sentaku.ContextualMethod()

    def all(self):
        zone_collection = self.appliance.rest_api.collections.zones
        zones = []
        parent = self.filters.get('parent')
        for zone in zone_collection:
            zone.reload(attributes=['region_number'])
            if parent and zone.region_number != parent.number:
                continue
            zones.append(self.instantiate(
                name=zone.name, description=zone.description, id=zone.id
            ))
        # TODO: This code needs a refactor once the attributes can be loaded from the collection
        return zones


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
    # all = sentaku.ContextualMethod()

    ENTITY = Region

    def all(self):
        self.appliance.rest_api.collections.regions.reload()
        region_collection = self.appliance.rest_api.collections.regions
        regions = [self.instantiate(region.region) for region in region_collection]
        return regions

from . import ui, ssui, rest  # NOQA last for import cycles
importscan.scan(ui)
importscan.scan(ssui)
importscan.scan(rest)
