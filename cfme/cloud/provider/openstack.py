import attr

from wrapanapi.systems import OpenstackSystem

from cfme.cloud.instance.openstack import OpenStackInstance
from cfme.common.provider import EventsEndpoint
from cfme.exceptions import ItemNotFound
from cfme.infrastructure.provider.openstack_infra import RHOSEndpoint, OpenStackInfraEndpointForm
from cfme.services.catalogs.catalog_items import OpenStackCatalogItem
from . import CloudProvider


@attr.s(hash=False)
class OpenStackProvider(CloudProvider):
    """
     BaseProvider->CloudProvider->OpenStackProvider class.
     represents CFME provider and operations available in UI
    """
    catalog_item_type = OpenStackCatalogItem
    type_name = "openstack"
    mgmt_class = OpenstackSystem
    vm_class = OpenStackInstance
    db_types = ["Openstack::CloudManager"]
    endpoints_form = OpenStackInfraEndpointForm
    settings_key = 'ems_openstack'
    log_name = 'fog'

    # xpath locators for elements, to be used by selenium
    _console_connection_status_element = '//*[@id="noVNC_status"]'
    _canvas_element = '//*[@id="noVNC_canvas"]'
    _ctrl_alt_del_xpath = '//*[@id="sendCtrlAltDelButton"]'

    api_port = attr.ib(default=None)
    api_version = attr.ib(default=None)
    sec_protocol = attr.ib(default=None)
    amqp_sec_protocol = attr.ib(default=None)
    keystone_v3_domain_id = attr.ib(default=None)
    tenant_mapping = attr.ib(default=None)
    infra_provider = attr.ib(default=None)

    # todo: move it to collections later
    def create(self, *args, **kwargs):
        # Override the standard behaviour to actually create the underlying infra first.
        if self.infra_provider:
            self.infra_provider.create(validate_credentials=True, validate_inventory=True,
                                       check_existing=True)
        kwargs['validate_credentials'] = kwargs.get('validate_credentials', True)
        return super(OpenStackProvider, self).create(*args, **kwargs)

    def create_rest(self, *args, **kwargs):
        # Override the standard behaviour to actually create the underlying infra first.
        if self.infra_provider:
            self.infra_provider.create_rest(validate_inventory=True,
                                            check_existing=True)
        return super(OpenStackProvider, self).create_rest(*args, **kwargs)

    @property
    def view_value_mapping(self):
        if self.infra_provider is None:
            # Don't look for the selectbox; it's either not there or we don't care what's selected
            infra_provider_name = None
        elif self.infra_provider is False:
            # Select nothing (i.e. deselect anything that is potentially currently selected)
            infra_provider_name = "---"
        else:
            infra_provider_name = self.infra_provider.name
        return {
            'name': self.name,
            'prov_type': 'OpenStack',
            'region': None,
            'infra_provider': infra_provider_name,
            'tenant_mapping': getattr(self, 'tenant_mapping', None),
            'api_version': self.api_version,
            'keystone_v3_domain_id': self.keystone_v3_domain_id
        }

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines """
        if ('network_name' not in deploy_args) and self.data.get('network'):
            return {'network_name': self.data['network']}
        return {}

    @classmethod
    def from_config(cls, prov_config, prov_key):
        endpoints = {}
        endpoints[RHOSEndpoint.name] = RHOSEndpoint(**prov_config['endpoints'][RHOSEndpoint.name])

        endp_name = EventsEndpoint.name
        if prov_config['endpoints'].get(endp_name):
            endpoints[endp_name] = EventsEndpoint(**prov_config['endpoints'][endp_name])

        from cfme.utils.providers import get_crud
        infra_prov_key = prov_config.get('infra_provider_key')
        infra_provider = get_crud(infra_prov_key) if infra_prov_key else None

        return cls.appliance.collections.cloud_providers.instantiate(
            prov_class=cls,
            name=prov_config['name'],
            api_port=prov_config['port'],
            api_version=prov_config.get('api_version', 'Keystone v2'),
            endpoints=endpoints,
            zone=prov_config['server_zone'],
            key=prov_key,
            keystone_v3_domain_id=prov_config.get('domain_id'),
            sec_protocol=prov_config.get('sec_protocol', "Non-SSL"),
            tenant_mapping=prov_config.get('tenant_mapping', False),
            infra_provider=infra_provider)

    # Following methods will only work if the remote console window is open
    # and if selenium focused on it. These will not work if the selenium is
    # focused on Appliance window.
    def get_console_connection_status(self):
        try:
            return self.appliance.browser.widgetastic.selenium.find_element_by_xpath(
                self._console_connection_status_element).text
        except:
            raise ItemNotFound("Element not found on screen, is current focus on console window?")

    def get_remote_console_canvas(self):
        try:
            return self.appliance.browser.widgetastic.selenium.find_element_by_xpath(
                self._canvas_element)
        except:
            raise ItemNotFound("Element not found on screen, is current focus on console window?")

    def get_console_ctrl_alt_del_btn(self):
        try:
            return self.appliance.browser.widgetastic.selenium.find_element_by_xpath(
                self._ctrl_alt_del_xpath)
        except:
            raise ItemNotFound("Element not found on screen, is current focus on console window?")
