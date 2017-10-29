from navmazing import NavigateToSibling
from widgetastic.widget import View, Text
from widgetastic_patternfly import Tab, Input, BootstrapSelect, Button
from widgetastic_manageiq import Checkbox, RadioGroup, FileInput, Table
from wrapanapi.openstack_infra import OpenstackInfraSystem

from cfme.infrastructure.provider import InfraProvider
from cfme.common.provider import EventsEndpoint, SSHEndpoint, DefaultEndpoint, DefaultEndpointForm
from cfme.common.provider_views import BeforeFillMixin, ProviderNodesView
from cfme.utils.appliance.implementations.ui import navigate_to, CFMENavigateStep, navigator


class RHOSEndpoint(DefaultEndpoint):
    @property
    def view_value_mapping(self):
        return {'security_protocol': self.security_protocol,
                'hostname': self.hostname,
                'api_port': getattr(self, 'api_port', None)
                }


class OpenStackInfraEndpointForm(View):
    @View.nested
    class default(Tab, DefaultEndpointForm, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Default'
        security_protocol = BootstrapSelect('default_security_protocol')
        api_port = Input('default_api_port')

    @View.nested
    class events(Tab, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Events'
        event_stream = RadioGroup(locator='//div[@id="amqp"]')
        # below controls which appear only if amqp is chosen
        hostname = Input('amqp_hostname')
        api_port = Input('amqp_api_port')
        security_protocol = BootstrapSelect('amqp_security_protocol')
        change_password = Text(locator='.//a[normalize-space(.)="Change stored password"]')

        username = Input('amqp_userid')
        password = Input('amqp_password')
        confirm_password = Input('amqp_verify')

        validate = Button('Validate')

    @View.nested
    class rsa_keypair(Tab, BeforeFillMixin):  # NOQA
        TAB_NAME = 'RSA key pair'

        username = Input('ssh_keypair_userid')
        private_key = FileInput(locator='.//input[@id="ssh_keypair_password"]')
        change_key = Text(locator='.//a[normalize-space(.)="Change stored private key"]')


class OpenstackInfraProvider(InfraProvider):
    STATS_TO_MATCH = ['num_template', 'num_host']
    type_name = "openstack_infra"
    mgmt_class = OpenstackInfraSystem
    db_types = ["Openstack::InfraManager"]
    endpoints_form = OpenStackInfraEndpointForm
    hosts_menu_item = "Nodes"
    bad_credentials_error_msg = (
        'Credential validation was not successful: ',
        'Login failed due to a bad username or password.'
    )

    def __init__(self, name=None, endpoints=None, key=None, hostname=None, ip_address=None,
                 start_ip=None, end_ip=None, provider_data=None, appliance=None):
        super(OpenstackInfraProvider, self).__init__(name=name, endpoints=endpoints, key=key,
                                                     provider_data=provider_data,
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
            'prov_type': 'OpenStack Platform Director',
        }

    def has_nodes(self):
        details_view = navigate_to(self, 'Details')
        try:
            details_view.entities.relationships.get_text_of('Hosts')
            return False
        except NameError:
            return int(details_view.entities.relationships.get_text_of('Hosts / Nodes')) > 0

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        endpoints = {}
        for endp in prov_config['endpoints']:
            for expected_endpoint in (RHOSEndpoint, EventsEndpoint, SSHEndpoint):
                if expected_endpoint.name == endp:
                    endpoints[endp] = expected_endpoint(**prov_config['endpoints'][endp])

        if prov_config.get('discovery_range'):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')
        return cls(
            name=prov_config['name'],
            endpoints=endpoints,
            key=prov_key,
            start_ip=start_ip,
            end_ip=end_ip,
            appliance=appliance)

    def register(self, file_path):
        """Register new nodes (Openstack)
        Fill a form for new host with json file format
        This function is valid only for RHOS10 and above

        Args:
            file_path: file path of json file with new node details, navigation
                       MUST be from a specific self
        """
        view = navigate_to(self, 'RegisterNodes')
        view.fill({'file': file_path})
        view.register.click()
        exp_msg = 'Nodes were added successfully. Refresh queued.'
        self.create_view(ProviderNodesView).flash.assert_success_message(exp_msg)

    def scale_down(self):
        """Scales down provider"""
        view = navigate_to(self, 'ScaleDown')
        view.checkbox.click()
        view.scale_down.click()
        self.create_view(ProviderNodesView).flash.assert_no_error()

    def scale_out(self, increase_by=1):
        """Scale out Openstack Infra provider
        Args:
            increase_by - count of nodes to be added to infra provider
        """
        view = navigate_to(self, 'ScaleOut')
        curr_compute_count = int(view.compute_count.value)
        view.compute_count.fill(curr_compute_count + increase_by)
        view.scale.click()
        self.create_view(ProviderNodesView).flash.assert_no_error()

    def node_exist(self, name='my_node'):
        """" registered imported host exist
        This function is valid only for RHOS10 and above

        Args:
            name: by default name is my_name Input self, name of the new node,
                  looking for the host in Ironic clients, compare the record found with
                  hosts list in CFME DB

        Returns: boolean value if host found
        """
        nodes = self.mgmt.list_node()
        nodes_dict = {i.name: i for i in nodes}
        query = self.appliance.db.client.session.query(
            self.appliance.db.client['hosts'], 'guid')
        node_uuid = str(nodes_dict[name])
        for db_node in query.all():
            return db_node.hosts.name == str(node_uuid.uuid)


class ProviderRegisterNodesView(View):
    """
     represents Register Nodes view
    """
    file = FileInput(locator='//input[@id="nodes_json_file"]')
    register = Button(value='Register')
    cancel = Button(value='Cancel')

    @property
    def is_displayed(self):
        return False


class ProviderScaleDownView(View):
    """
     represents Scale down view
    """
    table = Table(locator='//div[contains(@class, "form-horizontal")]//table')
    checkbox = Checkbox(name='host_ids[]')
    scale_down = Button('Scale Down')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return False


class ProviderScaleOutView(View):
    """
     represents Scale view
    """

    compute_count = Input(name='ComputeCount')
    scale = Button('Scale')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return False


@navigator.register(OpenstackInfraProvider, 'RegisterNodes')
class ProviderRegisterNodes(CFMENavigateStep):
    VIEW = ProviderRegisterNodesView
    prerequisite = NavigateToSibling('ProviderNodes')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Register Nodes')


@navigator.register(OpenstackInfraProvider, 'ScaleDown')
class ProviderScaleDown(CFMENavigateStep):
    VIEW = ProviderScaleDownView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        item_title = 'Scale this Infrastructure Provider down'
        self.prerequisite_view.toolbar.configuration.item_select(item_title)


@navigator.register(OpenstackInfraProvider, 'ScaleOut')
class ProviderScaleOut(CFMENavigateStep):
    VIEW = ProviderScaleOutView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        item_title = 'Scale this Infrastructure Provider'
        self.prerequisite_view.toolbar.configuration.item_select(item_title)
