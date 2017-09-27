from wrapanapi.openstack import OpenstackSystem

from . import CloudProvider
from cfme.common.provider import EventsEndpoint
from cfme.infrastructure.provider.openstack_infra import RHOSEndpoint, OpenStackInfraEndpointForm
from cfme.exceptions import ItemNotFound


class OpenStackProvider(CloudProvider):
    """
     BaseProvider->CloudProvider->OpenStackProvider class.
     represents CFME provider and operations available in UI
    """
    type_name = "openstack"
    mgmt_class = OpenstackSystem
    db_types = ["Openstack::CloudManager"]
    endpoints_form = OpenStackInfraEndpointForm
    # xpath locators for elements, to be used by selenium
    _console_connection_status_element = '//*[@id="noVNC_status"]'
    _canvas_element = '//*[@id="noVNC_canvas"]'
    _ctrl_alt_del_xpath = '//*[@id="sendCtrlAltDelButton"]'

    def __init__(self, name=None, endpoints=None, zone=None, key=None, hostname=None,
                 ip_address=None, api_port=None, api_version=None, sec_protocol=None,
                 amqp_sec_protocol=None, keystone_v3_domain_id=None, tenant_mapping=None,
                 infra_provider=None, appliance=None):
        super(OpenStackProvider, self).__init__(name=name, endpoints=endpoints,
                                                zone=zone, key=key, appliance=appliance)
        self.hostname = hostname
        self.ip_address = ip_address
        self.api_port = api_port
        self.api_version = api_version
        self.keystone_v3_domain_id = keystone_v3_domain_id
        self.infra_provider = infra_provider
        self.sec_protocol = sec_protocol
        self.tenant_mapping = tenant_mapping
        self.amqp_sec_protocol = amqp_sec_protocol

    def create(self, *args, **kwargs):
        # Override the standard behaviour to actually create the underlying infra first.
        if self.infra_provider:
            self.infra_provider.create(validate_credentials=True, validate_inventory=True,
                                       check_existing=True)
        if self.appliance.version >= "5.6" and 'validate_credentials' not in kwargs:
            # 5.6 requires validation, so unless we specify, we want to validate
            kwargs['validate_credentials'] = True
        return super(OpenStackProvider, self).create(*args, **kwargs)

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
    def from_config(cls, prov_config, prov_key, appliance=None):
        endpoints = {}
        endpoints[RHOSEndpoint.name] = RHOSEndpoint(**prov_config['endpoints'][RHOSEndpoint.name])

        endp_name = EventsEndpoint.name
        if prov_config['endpoints'].get(endp_name):
            endpoints[endp_name] = EventsEndpoint(**prov_config['endpoints'][endp_name])

        from cfme.utils.providers import get_crud
        infra_prov_key = prov_config.get('infra_provider_key')
        infra_provider = get_crud(infra_prov_key, appliance=appliance) if infra_prov_key else None
        api_version = prov_config.get('api_version', None)

        if not api_version:
            api_version = 'Keystone v2'

        return cls(name=prov_config['name'],
                   hostname=prov_config['hostname'],
                   ip_address=prov_config['ipaddress'],
                   api_port=prov_config['port'],
                   api_version=api_version,
                   endpoints=endpoints,
                   zone=prov_config['server_zone'],
                   key=prov_key,
                   keystone_v3_domain_id=prov_config.get('domain_id', None),
                   sec_protocol=prov_config.get('sec_protocol', "Non-SSL"),
                   tenant_mapping=prov_config.get('tenant_mapping', False),
                   infra_provider=infra_provider,
                   appliance=appliance)

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
