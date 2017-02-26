from navmazing import NavigateToSibling, NavigationDestinationNotFound
from utils.appliance.implementations.ui import (navigate_to, CFMENavigateStep,
                                                navigator)
from cfme.web_ui import Form, FileInput, InfoBlock, fill
import cfme.web_ui.toolbar as tb
from cfme.web_ui import Region
from . import InfraProvider, prop_region
from mgmtsystem.openstack_infra import OpenstackInfraSystem
import cfme.fixtures.pytest_selenium as sel

details_page = Region(infoblock_type='detail')

register_nodes_form = Form(
    fields=[
        ('file', FileInput('nodes_json[file]')),
        ('register', "//*[@name='register']"),
        ('cancel', "//*[@name='cancel']")
    ])


@InfraProvider.add_provider_type
class OpenstackInfraProvider(InfraProvider):
    STATS_TO_MATCH = ['num_template', 'num_host']
    _properties_region = prop_region
    type_name = "openstack_infra"
    mgmt_class = OpenstackInfraSystem

    def __init__(self, name=None, credentials=None, key=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, provider_data=None,
                 sec_protocol=None):
        super(OpenstackInfraProvider, self).__init__(name=name, credentials=credentials,
                                             key=key, provider_data=provider_data)

        self.hostname = hostname
        self.ip_address = ip_address
        self.start_ip = start_ip
        self.end_ip = end_ip
        self.sec_protocol = sec_protocol

    def _form_mapping(self, create=None, **kwargs):
        data_dict = {
            'name_text': kwargs.get('name'),
            'type_select': create and 'OpenStack Platform Director',
            'hostname_text': kwargs.get('hostname'),
            'api_port': kwargs.get('api_port'),
            'ipaddress_text': kwargs.get('ip_address'),
            'sec_protocol': kwargs.get('sec_protocol'),
            'amqp_sec_protocol': kwargs.get('amqp_sec_protocol')}
        if 'amqp' in self.credentials:
            data_dict.update({
                'event_selection': 'amqp',
                'amqp_hostname_text': kwargs.get('hostname'),
                'amqp_api_port': kwargs.get('amqp_api_port', '5672'),
                'amqp_sec_protocol': kwargs.get('amqp_sec_protocol', "Non-SSL")
            })
        return data_dict

    def has_nodes(self):
        try:
            details_page.infoblock.text("Relationships", "Hosts")
            return False
        except sel.NoSuchElementException:
            return int(
                details_page.infoblock.text("Relationships", "Nodes")) > 0

    @classmethod
    def from_config(cls, prov_config, prov_key):
        credentials_key = prov_config['credentials']
        credentials = cls.process_credential_yaml_key(credentials_key)
        credential_dict = {'default': credentials}
        if prov_config.get('discovery_range', None):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')
        if 'ssh_credentials' in prov_config:
            credential_dict['ssh'] = OpenstackInfraProvider.process_credential_yaml_key(
                prov_config['ssh_credentials'], cred_type='ssh')
        if 'amqp_credentials' in prov_config:
            credential_dict['amqp'] = OpenstackInfraProvider.process_credential_yaml_key(
                prov_config['amqp_credentials'], cred_type='amqp')
        return cls(
            name=prov_config['name'],
            sec_protocol=prov_config.get('sec_protocol', "Non-SSL"),
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            credentials=credential_dict,
            key=prov_key,
            start_ip=start_ip,
            end_ip=end_ip)

    def register(self, file_path):
        """Register new nodes (Openstack)
        Fill a form for new host with json file format
        This function is valid only for RHOS10 and above
        Args:
            file_path - file path of json file with new node details, navigation
             MUST be from a specific self
        """
        try:
            navigate_to(self, 'ProviderNodes')
        except NavigationDestinationNotFound:
            assert "Missing nodes in provider's details"
        tb.select('Configuration', 'Register Nodes')
        my_form = {'file': file_path}
        fill(register_nodes_form, my_form, action=register_nodes_form.register)

    def node_exist(self, name='my_node'):
        """" registered imported host exist
        This function is valid only for RHOS10 and above
        Args:
            name - by default name is my_name Input self, name of the new node,
             looking for the host in Ironic clients, compare the record found with
              hosts list in CFME DB
        Returns: boolean value if host found
        """
        nodes = self.mgmt.list_node()
        nodes_dict = {i.name: i for i in nodes}
        query = self.appliance.db.session.query(
            self.appliance.db['hosts'], 'guid')
        node_uuid = str(nodes_dict[name])
        for db_node in query.all():
            return db_node.hosts.name == str(node_uuid.uuid)


@navigator.register(OpenstackInfraProvider, 'ProviderNodes')
class ProviderNodes(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element("Relationships", "Nodes"))
