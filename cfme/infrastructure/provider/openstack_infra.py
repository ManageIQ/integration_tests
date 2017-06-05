from navmazing import NavigateToSibling

from . import InfraProvider, prop_region
from cfme.common.provider_views import ProviderNodesView, ProviderRegisterNodesView
from cfme.exceptions import DestinationNotFound
from mgmtsystem.openstack_infra import OpenstackInfraSystem
from utils.appliance.implementations.ui import navigate_to, CFMENavigateStep, navigator


class OpenstackInfraProvider(InfraProvider):
    STATS_TO_MATCH = ['num_template', 'num_host']
    _properties_region = prop_region
    type_name = "openstack_infra"
    mgmt_class = OpenstackInfraSystem
    db_types = ["Openstack::InfraManager"]

    def __init__(self, name=None, credentials=None, key=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, provider_data=None,
                 sec_protocol=None, appliance=None):
        super(OpenstackInfraProvider, self).__init__(
            name=name, credentials=credentials, key=key, provider_data=provider_data,
            appliance=appliance)

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
        details_view = navigate_to(self, 'Details')
        try:
            details_view.contents.relationships.get_text_of('Hosts')
            return False
        except NameError:
            return int(details_view.contents.relationships.get_text_of('Hosts / Nodes')) > 0

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
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
            end_ip=end_ip,
            appliance=appliance)

    def register(self, file_path):
        """Register new nodes (Openstack)
        Fill a form for new host with json file format
        This function is valid only for RHOS10 and above
        Args:
            file_path - file path of json file with new node details, navigation
             MUST be from a specific self
        """
        view = navigate_to(self, 'RegisterNodes')
        view.fill({'file': file_path})
        view.register.click()

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
    VIEW = ProviderNodesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        view = self.prerequisite_view
        try:
            view.contents.relationships.click_at('Nodes')
        except NameError:
            raise DestinationNotFound("Nodes aren't present on details page of this provider")


@navigator.register(OpenstackInfraProvider, 'RegisterNodes')
class ProviderRegisterNodes(CFMENavigateStep):
    VIEW = ProviderRegisterNodesView
    prerequisite = NavigateToSibling('ProviderNodes')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Register Nodes')
