import sentaku

from cfme.utils.appliance import Navigatable
from cfme.utils.pretty import Pretty


class Server(Navigatable, sentaku.modeling.ElementMixin):
    def __init__(self, appliance, zone=None, name="EVM", sid=1):
        Navigatable.__init__(self, appliance=appliance)
        self.zone = zone or appliance.server.zone
        self.name = name
        self.sid = sid
        self.zone.servers.add(self)
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


class ZoneCollection(Navigatable, sentaku.modeling.ElementMixin):

    create = sentaku.ContextualMethod()

    def __init__(self, appliance, region=None):
        self.appliance = appliance
        self.region = region or appliance.server.zone.region
        self.parent = self.appliance.context


class Zone(Pretty, Navigatable, sentaku.modeling.ElementMixin):
    """ Configure/Configuration/Region/Zones functionality

    Create/Read/Update/Delete functionality.
    """
    pretty_attrs = ['name', 'description', 'smartproxy_ip', 'ntp_servers',
                    'max_scans', 'user']

    exists = sentaku.ContextualProperty()
    update = sentaku.ContextualMethod()
    delete = sentaku.ContextualMethod()

    def __init__(self, appliance, region=None,
            name=None, description=None, smartproxy_ip=None, ntp_servers=None, max_scans=None,
            user=None):
        self.appliance = appliance
        self.servers = set()
        self.region = region or self.appliance.server.zone.region
        self.name = name or "default"
        self.description = description or "Default Zone"
        self.region.zones.add(self)

        self.smartproxy_ip = smartproxy_ip
        self.ntp_servers = ntp_servers
        self.max_scans = max_scans
        self.user = user
        self.parent = self.appliance.context


class Region(Navigatable, sentaku.modeling.ElementMixin):
    def __init__(self, appliance, number=0):
        self.appliance = appliance
        self.zones = set()
        self.number = number
        self.parent = self.appliance.context

    @property
    def settings_string(self):
        return "{} Region: Region {} [{}]".format(
            self.appliance.product_name, self.number, self.number)

from . import ui, ssui  # NOQA last for import cycles
sentaku.register_external_implementations_in(ui, ssui)
