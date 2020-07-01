import json

import attr
import importscan
import sentaku
from cached_property import cached_property

from cfme.exceptions import RestLookupError
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.modeling.base import parent_of_type
from cfme.utils import ParamClassName
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty


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
        return getattr(self.appliance._rest_api_server, 'name', '')

    @property
    def current_string(self):
        """Returns the string ' (current)' if the appliance serving the UI request
         matches this server instance. Used to generate the appropriate tree_path
         for navigating configuration accordion trees."""
        return ' (current)' if self.sid == self.appliance.server_id() else ''

    @property
    def tree_path(self):
        """Generate the path list for navigation purposes
        list elements follow the tree path in the configuration accordion

        Returns:
            list of path elements for tree navigation
        """
        name_string = f' {self.name} '.replace('  ', ' ')
        path = [
            self.zone.region.settings_string,
            "Zones",
            f"Zone: {self.zone.title_string()}",
            f"Server:{name_string}[{self.sid}]{self.current_string}"  # variables have needed spaces
        ]
        return path

    @property
    def diagnostics_tree_path(self):
        """Generate tree path list for the diagnostics tree in the configuration accordion"""
        path = self.tree_path
        path.remove("Zones")
        return path

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
        entity = self.rest_api_entity
        entity.reload(attributes=['zone'])
        return self.appliance.collections.zones.instantiate(
            name=entity.zone['name'],
            description=entity.zone['description'],
            id=entity.zone['id']
        )

    @property
    def slave_servers(self):
        return self.zone.collections.servers.filter({'slave': True}).all()

    @property
    def is_slave(self):
        return self in self.slave_servers

    @property
    def secondary_servers(self):
        """ Find and return a list of all other servers in this server's zone. """
        return [s for s in self.zone.collections.servers.all() if s.sid != self.sid]

    @property
    def _api_settings_url(self):
        return '/'.join(
            [self.appliance.rest_api.collections.servers._href, str(self.sid), 'settings']
        )

    @property
    def rest_api_entity(self):
        try:
            return self.appliance.rest_api.collections.servers.get(id=self.sid)
        except ValueError:
            raise RestLookupError(f'No server rest entity found matching ID {self.sid}')

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
        """Look for the master server through REST entity, use its ID to
        instantiate Server

        In replicated environment, we can have more than one master. In such
        case one of them (quite randomly thus quite possibly the incorrect one)
        used to be selected by the get_master function.

        To get the the correct rest-api object matching the appliance in the
        context the IPAppliance._rest_api_server has to be used .

        Returns:
            :py:class:`cfme.base.Server` entity
        """
        collect = self.appliance.rest_api.collections.servers
        servers = collect.all if self.appliance.is_dev else collect.find_by(is_master=True)
        server, = servers

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

    @cached_property
    def region(self):
        possible_parent = parent_of_type(self, Region)
        if possible_parent:
            return possible_parent
        else:
            zone_res = self.appliance.rest_api.collections.zones.find_by(id=self.id)
            zone, = zone_res
            zone.reload(attributes=['region_number'])
            return self.appliance.collections.regions.instantiate(number=zone.region_number)

    @property
    def _api_settings_url(self):
        return '/'.join([self.appliance.rest_api.collections.zones._href, str(self.id), 'settings'])

    @property
    def advanced_settings(self):
        """"GET zones/:id/settings api endpoint to query zone configuration"""
        return self.appliance.rest_api.get(self._api_settings_url)

    @property
    def current_string(self):
        """Returns the string ' (current)' if the appliance serving the UI request is in this zone.
        Used to generate the appropriate tree_path for navigating configuration accordion trees."""
        return ' (current)' if (
            self.id == self.appliance.server.zone.id
        ) else ''

    def title_string(self, quote_str=''):
        """Used to generate the title.text for Zone-related views.

        Returns a string of the form:

        "Zone Description" (current)
        [or]
        "Zone Description"

        Args:
            quote_str: The optional string to include before and after the
                       zone description. To reproduce the title.text as shown
                       above, quote_str='"'.

                       In accordion trees, the zone appears in the form:

                       Zone Description (current)
                       [or]
                       Zone Description

                       (without the quotation marks surrounding the
                       description). In this case, we can pass
                       quote_str='' (the default).
        """
        return f"{quote_str}{self.description}{quote_str}{self.current_string}"

    @property
    def tree_path(self):
        """Generate the tree path list for the settings tree in the configuration accordion

        Returns:
            list of path elements for tree navigation
        """
        path = [
            self.region.settings_string,
            "Zones",
            f"Zone: {self.title_string()}"
        ]
        return path

    @property
    def diagnostics_tree_path(self):
        """Generate tree path list for the diagnostics tree in the configuration accordion"""
        path = self.tree_path
        path.remove("Zones")
        return path

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

    @property
    def rest_api_entity(self):
        try:
            return self.appliance.rest_api.collections.zones.get(id=self.id)
        except ValueError:
            raise RestLookupError(f"No zone rest entity found matching id '{self.id}'")


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
        # TODO: This does not work when region description is not set to default.
        return f"{self.appliance.product_name} Region: Region {self.number} [{self.number}]"

    @property
    def region_string(self):
        """
        Return Region string like `Region 0`
        TODO: This does not work when region description is not set to default.
        """
        return f"Region {self.number}"

    @property
    def tree_path(self):
        return [self.settings_string]

    @property
    def zones_tree_path(self):
        path = self.tree_path
        path.append("Zones")
        return path

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
        filter_query = f'?expand=resources&filter[]=region={self.number}'
        region_filter = self.appliance.rest_api.get(
            f'{self.appliance.rest_api.collections.regions._href}{filter_query}'
        )
        region, = region_filter['resources']
        return '/'.join([self.appliance.rest_api.collections.regions._href,
                         str(region['id']),
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

    @property
    def rest_api_entity(self):
        try:
            return self.appliance.rest_api.collections.regions.get(region_number=self.number)
        except ValueError:
            raise RestLookupError(
                f"No region rest entity found matching region_number {self.number}"
            )


@attr.s
class RegionCollection(BaseCollection, sentaku.modeling.ElementMixin):
    # all = sentaku.ContextualMethod()

    ENTITY = Region

    def all(self):
        self.appliance.rest_api.collections.regions.reload()
        region_collection = self.appliance.rest_api.collections.regions
        regions = [self.instantiate(region.region) for region in region_collection]
        return regions


from cfme.base import ui, ssui, rest  # NOQA last for import cycles
importscan.scan(ui)
importscan.scan(ssui)
importscan.scan(rest)
