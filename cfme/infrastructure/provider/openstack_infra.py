from navmazing import NavigateToSibling
from widgetastic.widget import View, Text

from . import InfraProvider, prop_region
from cfme import BaseLoggedInPage
from cfme.exceptions import DestinationNotFound
from mgmtsystem.openstack_infra import OpenstackInfraSystem
from utils.appliance.implementations.ui import navigate_to, CFMENavigateStep, navigator
from widgetastic_manageiq import Button, FileInput, PaginationPane
from .widgetastic_views import NodesToolBar


class InfraProviderRegisterNodesView(View):
    file = FileInput(locator='//input[@id="nodes_json_file"]')
    register = Button('Register')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return False


class InfraProviderNodesView(BaseLoggedInPage):
    # todo: to add the rest a bit later
    title = Text('//div[@id="main-content"]//h1')

    @View.nested
    class toolbar(NodesToolBar):
        pass

    @View.nested
    class contents(View):
        pass

    @View.nested
    class paginator(PaginationPane):
        pass

    @property
    def is_displayed(self):
        title = '{name} (All Managed Hosts)'.format(name=self.context['object'].name)
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and \
            self.title.text == title


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
        main_values = {
            'name': kwargs.get('name'),
            'prov_type': create and 'OpenStack Platform Director',
        }

        endpoint_values = {
            'default': {
                'hostname': kwargs.get('hostname'),
                # 'ipaddress_text': kwargs.get('ip_address'),
                'api_port': kwargs.get('api_port'),
                'security_protocol': kwargs.get('sec_protocol'),
            },
            'events': {
                'security_protocol': kwargs.get('amqp_sec_protocol'),
            }
        }
        if 'amqp' in self.credentials:
            endpoint_values['events'].update({
                'event_stream': 'AMQP',
                'hostname': kwargs.get('hostname'),
                'api_port': kwargs.get('amqp_api_port', '5672'),
                'security_protocol': kwargs.get('amqp_sec_protocol', "Non-SSL")
            })
        return main_values, endpoint_values

    def has_nodes(self):
        details_view = navigate_to(self, 'Details')
        view_selector = details_view.toolbar.view_selector
        if view_selector.selected != 'Summary View':
            view_selector.select('Summary View')
        try:
            details_view.contents.relationships.get_text_of('Hosts')
            return False
        except NameError:
            return int(details_view.contents.relationships.get_text_of('Nodes')) > 0

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
        nodes_view = navigate_to(self, 'ProviderNodes')
        nodes_view.toolbar.configuration.item_select('Register Nodes')
        reg_form = self.create_view(InfraProviderRegisterNodesView)
        reg_form.fill({'file': file_path})
        reg_form.register.click()

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
    VIEW = InfraProviderNodesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        view = self.prerequisite_view
        view_selector = view.toolbar.view_selector
        if view_selector.selected != 'Summary View':
            view_selector.select('Summary View')
        try:
            view.contents.relationships.click_at('Nodes')
        except NameError:
            raise DestinationNotFound("Nodes aren't present on details page of this provider")
