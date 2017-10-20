from widgetastic.widget import View, Text
from widgetastic_patternfly import Tab, Input, BootstrapSwitch, Button

from cfme.common.provider_views import BeforeFillMixin
from cfme.utils import version
from . import InfraProvider
from cfme.common.provider import CANDUEndpoint, DefaultEndpoint, DefaultEndpointForm
from wrapanapi.rhevm import RHEVMSystem
from cfme.exceptions import ItemNotFound


class RHEVMEndpoint(DefaultEndpoint):
    @property
    def view_value_mapping(self):
        return {'hostname': self.hostname,
                'api_port': getattr(self, 'api_port', None),
                'verify_tls': version.pick({version.LOWEST: None,
                                            '5.8': getattr(self, 'verify_tls', None)}),
                'ca_certs': version.pick({version.LOWEST: None,
                                          '5.8': getattr(self, 'ca_certs', None)})
                }


class RHEVMEndpointForm(View):
    @View.nested
    class default(Tab, DefaultEndpointForm, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Default'
        api_port = Input('default_api_port')
        verify_tls = BootstrapSwitch(id='default_tls_verify')
        ca_certs = Input('default_tls_ca_certs')

    @View.nested
    class candu(Tab, BeforeFillMixin):  # NOQA
        TAB_NAME = 'C & U Database'
        hostname = Input('metrics_hostname')
        api_port = Input('metrics_api_port')
        database_name = Input('metrics_database_name')
        username = Input('metrics_userid')
        password = Input('metrics_password')
        confirm_password = Input('metrics_verify')
        change_password = Text(locator='.//a[normalize-space(.)="Change stored password"]')

        validate = Button('Validate')


class RHEVMProvider(InfraProvider):
    type_name = "rhevm"
    mgmt_class = RHEVMSystem
    db_types = ["Redhat::InfraManager"]
    endpoints_form = RHEVMEndpointForm
    discover_dict = {"rhevm": True}
    # xpath locators for elements, to be used by selenium
    _console_connection_status_element = '//*[@id="connection-status"]|//*[@id="message-div"]'
    _canvas_element = '(//*[@id="remote-console"]/canvas|//*[@id="spice-screen"]/canvas)'
    _ctrl_alt_del_xpath = '//*[@id="ctrlaltdel"]'
    _fullscreen_xpath = '//*[@id="fullscreen"]'
    bad_credentials_error_msg = 'Cannot complete login due to an incorrect user name or password.'

    def __init__(self, name=None, endpoints=None, zone=None, key=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, provider_data=None, appliance=None):
        super(RHEVMProvider, self).__init__(
            name=name, endpoints=endpoints, zone=zone, key=key, provider_data=provider_data,
            appliance=appliance)
        self.hostname = hostname
        self.start_ip = start_ip
        self.end_ip = end_ip
        if ip_address:
            self.ip_address = ip_address

    @property
    def view_value_mapping(self):
        return {
            'name': self.name,
            'prov_type': version.pick({version.LOWEST: 'Red Hat Enterprise Virtualization Manager',
                                       '5.7.1': 'Red Hat Virtualization Manager',
                                       '5.7.3': 'Red Hat Virtualization',
                                       '5.8': 'Red Hat Virtualization Manager',
                                       '5.8.0.10': 'Red Hat Virtualization'}),
        }

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines """
        if 'default_cluster' not in deploy_args:
            return {'cluster': self.data['default_cluster']}
        return {}

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        endpoints = {}
        for endp in prov_config['endpoints']:
            for expected_endpoint in (RHEVMEndpoint, CANDUEndpoint):
                if expected_endpoint.name == endp:
                    endpoints[endp] = expected_endpoint(**prov_config['endpoints'][endp])

        if prov_config.get('discovery_range'):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')
        return cls(name=prov_config['name'],
                   endpoints=endpoints,
                   zone=prov_config.get('server_zone', 'default'),
                   key=prov_key,
                   start_ip=start_ip,
                   end_ip=end_ip,
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

    def get_console_fullscreen_btn(self):
        try:
            return self.appliance.browser.widgetastic.selenium.find_element_by_xpath(
                self._fullscreen_xpath)
        except:
            raise ItemNotFound("Element not found on screen, is current focus on console window?")
