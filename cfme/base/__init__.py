import json

import attr
import importscan
import sentaku

from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils import ParamClassName
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker

from cfme.utils.single import single

@attr.s
class Server(BaseEntity, sentaku.modeling.ElementMixin):
    _param_name = ParamClassName('name')

    sid = attr.ib(default=1)

    address = sentaku.ContextualMethod()
    login = sentaku.ContextualMethod()
    login_admin = sentaku.ContextualMethod()
    logout = sentaku.ContextualMethod()
    update_password = sentaku.ContextualMethod()
    logged_in = sentaku.ContextualMethod()
    current_full_name = sentaku.ContextualMethod()
    current_username = sentaku.ContextualMethod()
    current_group_name = sentaku.ContextualMethod()
    group_names = sentaku.ContextualMethod()
    intel_name = VersionPicker({"5.11": "Overview", Version.lowest(): "Cloud Intel"})

    # zone = sentaku.ContextualProperty()
    # slave_servers = sentaku.ContextualProperty()

    @property
    def name(self):
        """Fetch the name from the master server api entity

        Returns:
            string if entity has the name attribute
            None if its missing
        """
        # empty string default for string building w/o None
        return getattr(self.appliance._rest_api_server(), 'name', '')

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
        server = single(server_res)
        server.reload(attributes=['zone'])
        zone = server.zone
        zone_obj = self.appliance.collections.zones.instantiate(
            name=zone['name'], description=zone['description'], id=zone['id']
        )
        return zone_obj

    @property
    def slave_servers(self):
        return self.zone.collections.servers.filter({'slave': True}).all()

    @property
    def _api_settings_url(self):
        return '/'.join(
            [self.appliance.rest_api.collections.servers._href, str(self.sid), 'settings']
        )

    @property
    def advanced_settings(self):
        """GET servers/:id/settings api endpoint to query server configuration"""
        return self.appliance.rest_api.get(self._api_settings_url)

    def update_advanced_settings(self, settings_dict):
        """PATCH settings from the server's api/server/:id/settings endpoint

        Args:
            settings_dict: dictionary of the changes to be made to the yaml configuration
                       JSON dumps settings_dict to pass as raw hash data to rest_api session
        Raises:
            AssertionError: On an http result >=400 (RequestsResponse.ok)
        """
        # Calling the _session patch method because the core patch will wrap settings_dict in a list
        # Failing with some settings_dict, like 'authentication'
        # https://bugzilla.redhat.com/show_bug.cgi?id=1553394
        result = self.appliance.rest_api._session.patch(
            url=self._api_settings_url,
            data=json.dumps(settings_dict)
        )
        assert result.ok

    def upload_custom_logo(self, file_type, file_data=None, enable=True):
        """
        This function can be used to upload custom logo or text and use them.

        Args:
            file_type (str) : Can be either of [logo, login_logo, brand, favicon, logintext]
            file_data (str) : Text data if file_type is logintext else image path to be uploaded
            enable (bool) : True to use the custom logo/text else False
        """
        view = navigate_to(self, "CustomLogos")
        try:
            logo_view = getattr(view.customlogos, file_type)
        except AttributeError:
            raise AttributeError(
                "File type not in ('logo', 'login_logo', 'brand', 'favicon', 'logintext)."
            )
        if file_data:
            if file_type == "logintext":
                logo_view.fill({"login_text": file_data})
            else:
                logo_view.fill({"image": file_data})
                logo_view.upload_button.click()
            view.flash.assert_no_error()
        logo_view.enable.fill(enable)
        view.customlogos.save_button.click()
        view.flash.assert_no_error()


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
            servers.append(self.instantiate(sid=server.id))
        # TODO: This code needs a refactor once the attributes can be loaded from the collection
        return servers

    def get_master(self):
        """Look for the master server through REST entity, use its ID to instantiate Server

        Returns:
            :py:class:`cfme.base.Server` entity
        """
        collect = self.appliance.rest_api.collections.servers
        servers = collect.all if self.appliance.is_dev else collect.find_by(is_master=True)
        server = single(servers)

        if not hasattr(server, 'name'):
            logger.warning('rest_api server object has no name attribute')

        return self.instantiate(sid=server.id)


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
        zone = single(zone_res)
        zone.reload(attributes=['region_number'])
        region_obj = self.appliance.collections.regions.instantiate(number=zone.region_number)
        return region_obj

    @property
    def _api_settings_url(self):
        return '/'.join([self.appliance.rest_api.collections.zones._href, str(self.id), 'settings'])

    @property
    def advanced_settings(self):
        """"GET zones/:id/settings api endpoint to query zone configuration"""
        return self.appliance.rest_api.get(self._api_settings_url)

    def update_advanced_settings(self, settings_dict):
        """PATCH settings from the zone's api/zones/:id/settings endpoint

        Args:
            settings_dict: dictionary of the changes to be made to the yaml configuration
                       JSON dumps settings_dict to pass as raw hash data to rest_api session
        Raises:
            AssertionError: On an http result >=400 (RequestsResponse.ok)
        """
        # Calling the _session patch method because the core patch will wrap settings_dict in a list
        result = self.appliance.rest_api._session.patch(
            url=self._api_settings_url,
            data=json.dumps(settings_dict)
        )
        assert result.ok


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
            # starting in 5.11 there's a maintenance zone that is not shown in the UI but
            # is visible in API. We need to skip it for the correct navigation.
            # https://bugzilla.redhat.com/show_bug.cgi?id=1455145
            maintenance = 'Maintenance Zone'
            if (parent and zone.region_number != parent.number) or zone.description == maintenance:
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

    @property
    def _api_settings_url(self):
        """The region ID doesn't quite match the region number
        https://bugzilla.redhat.com/show_bug.cgi?id=1552899

        Look up the correct region ID for the object's region id (which is the 'number')

        Raises:
            KeyError if the region resource isn't found by the filter
            AssertionError if more than one region matches the filter
        """
        filter_query = '?expand=resources&filter[]=region={}'.format(self.number)
        region_filter = self.appliance.rest_api.get(
            '{}{}'.format(self.appliance.rest_api.collections.regions._href, filter_query)
        )
        region_id = single(region_filter['resources'])['id']
        return '/'.join([self.appliance.rest_api.collections.regions._href,
                         str(region_id),
                         'settings'])

    @property
    def advanced_settings(self):
        """"GET zones/:id/settings api endpoint to query region configuration"""
        return self.appliance.rest_api.get(self._api_settings_url)

    def update_advanced_settings(self, settings_dict):
        """PATCH settings from the zone's api/zones/:id/settings endpoint

        Args:
            settings_dict: dictionary of the changes to be made to the yaml configuration
                       JSON dumps settings_dict to pass as raw hash data to rest_api session
        Raises:
            AssertionError: On an http result >=400 (RequestsResponse.ok)
        """
        # Calling the _session patch method because the core patch will wrap settings_dict in a list
        result = self.appliance.rest_api._session.patch(
            url=self._api_settings_url,
            data=json.dumps(settings_dict)
        )
        assert result.ok

    def set_help_menu_configuration(self, config):
        """Set help configuration

        Args:
            config: dict with fields values
        """
        view = navigate_to(self, 'HelpMenu')
        view.fill({
            'documentation_title': config.get('documentation_title'),
            'documentation_url': config.get('documentation_url'),
            'documentation_type': config.get('documentation_type'),
            'product_title': config.get('product_title'),
            'product_url': config.get('product_url'),
            'product_type': config.get('product_type'),
            'about_title': config.get('about_title'),
            'about_url': config.get('about_url'),
            'about_type': config.get('about_type')
        })
        view.submit.click()
        view.flash.assert_no_error()


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
