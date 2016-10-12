from mgmtsystem.virtualcenter import VMWareSystem
from . import Provider
from cfme.web_ui import Form, Input, AngularSelect
from cfme.common.provider_endpoint import ProviderEndpoint


class DefaultEndpoint(ProviderEndpoint):
    form = Form(
        fields=[
            ('hostname', Input('default_hostname')),
            ('default_principal', Input("default_userid")),
            ('default_secret', Input("default_password")),
            ('default_verify_secret', Input("default_verify")),
        ])

    @classmethod
    def from_config(cls, conf_data):
        raw_credentials = VMwareProvider.get_raw_credentials(conf_data['credentials'])
        return cls({
            'hostname': conf_data['hostname'],
            'default_principal': raw_credentials['username'],
            'default_secret': raw_credentials['password'],
            'default_verify_secret': raw_credentials['password'],
        })


@Provider.add_provider_type
class VMwareProvider(Provider):
    type_name = "virtualcenter"
    mgmt_class = VMWareSystem
    properties_form = Form(
        fields=[
            ('type_select', AngularSelect("emstype")),
            ('name_text', Input("name")),
        ])

    def __init__(self, name=None, credentials=None, key=None, zone=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, provider_data=None,
                 endpoints=None):
        super(VMwareProvider, self).__init__(name=name, credentials=credentials,
                                             zone=zone, key=key, provider_data=provider_data)

        self.hostname = hostname
        self.ip_address = ip_address
        self.start_ip = start_ip
        self.end_ip = end_ip
        self.endpoints = endpoints

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'VMware vCenter'}

    @classmethod
    def from_config(cls, prov_config, prov_key):
        endpoints = {
            'default': DefaultEndpoint.from_config(prov_config['endpoints']['default'])
        }
        if prov_config.get('discovery_range', None):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')
        return cls(name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            endpoints=endpoints,
            zone=prov_config['server_zone'],
            key=prov_key,
            start_ip=start_ip,
            end_ip=end_ip)
