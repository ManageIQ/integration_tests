import attr
from navmazing import NavigateToSibling
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input
from wrapanapi.systems import OpenstackInfraSystem

from cfme.common.provider import DefaultEndpoint
from cfme.common.provider import DefaultEndpointForm
from cfme.common.provider import EventsEndpoint
from cfme.common.provider import SSHEndpoint
from cfme.common.provider_views import BeforeFillMixin
from cfme.common.provider_views import ProviderNodesView
from cfme.exceptions import displayed_not_implemented
from cfme.infrastructure.openstack_node import OpenstackNodeCollection
from cfme.infrastructure.provider import InfraProvider
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Checkbox
from widgetastic_manageiq import FileInput
from widgetastic_manageiq import RadioGroup
from widgetastic_manageiq import Table
from widgetastic_manageiq import WaitTab


class RHOSEndpoint(DefaultEndpoint):
    @property
    def view_value_mapping(self):
        return {'security_protocol': getattr(self, 'security_protocol', None),
                'hostname': getattr(self, 'hostname', None),
                'api_port': getattr(self, 'api_port', None)}


class OpenStackInfraEndpointForm(View):
    @View.nested
    class default(WaitTab, DefaultEndpointForm, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Default'
        security_protocol = BootstrapSelect('default_security_protocol')
        api_port = Input('default_api_port')

    @View.nested
    class events(WaitTab, BeforeFillMixin):  # NOQA
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
    class rsa_keypair(WaitTab, BeforeFillMixin):  # NOQA
        TAB_NAME = 'RSA key pair'

        username = Input('ssh_keypair_userid')
        private_key = FileInput(locator='.//input[@id="ssh_keypair_password"]')
        change_key = Text(locator='.//a[normalize-space(.)="Change stored private key"]')


@attr.s(cmp=False)
class OpenstackInfraProvider(InfraProvider):
    STATS_TO_MATCH = ['num_template', 'num_host']
    type_name = "openstack_infra"
    mgmt_class = OpenstackInfraSystem
    db_types = ["Openstack::InfraManager"]
    endpoints_form = OpenStackInfraEndpointForm
    ems_pretty_name = 'OpenStack Platform Director'
    hosts_menu_item = "Nodes"
    bad_credentials_error_msg = (
        'Credential validation was not successful: ',
        'Login failed due to a bad username or password.'
    )

    api_version = attr.ib(default=None)
    keystone_v3_domain_id = attr.ib(default=None)
    _collections = {'nodes': OpenstackNodeCollection}

    @property
    def view_value_mapping(self):
        return {
            'name': self.name,
            'prov_type': 'OpenStack Platform Director',
            'api_version': self.api_version,
            'keystone_v3_domain_id': self.keystone_v3_domain_id
        }

    @property
    def nodes(self):
        return self.collections.nodes

    def has_nodes(self):
        return bool(self.nodes.all())

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        appliance = appliance or cls.appliance
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
        return appliance.collections.infra_providers.instantiate(
            prov_class=cls,
            name=prov_config['name'],
            endpoints=endpoints,
            key=prov_key,
            start_ip=start_ip,
            end_ip=end_ip,
            api_version=prov_config.get('api_version', 'Keystone v2'),
            keystone_v3_domain_id=prov_config.get('domain_id'))

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

    is_displayed = displayed_not_implemented


class ProviderScaleDownView(View):
    """
     represents Scale down view
    """
    table = Table(locator='//div[contains(@class, "form-horizontal")]//table')
    checkbox = Checkbox(name='host_ids[]')
    scale_down = Button('Scale Down')
    cancel = Button('Cancel')

    is_displayed = displayed_not_implemented


class ProviderScaleOutView(View):
    """
     represents Scale view
    """

    compute_count = Input(name='ComputeCount')
    scale = Button('Scale')
    cancel = Button('Cancel')

    is_displayed = displayed_not_implemented


@navigator.register(OpenstackInfraProvider, 'RegisterNodes')
class ProviderRegisterNodes(CFMENavigateStep):
    VIEW = ProviderRegisterNodesView
    prerequisite = NavigateToSibling('ProviderNodes')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Register Nodes')


@navigator.register(OpenstackInfraProvider, 'ScaleDown')
class ProviderScaleDown(CFMENavigateStep):
    VIEW = ProviderScaleDownView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        item_title = 'Scale this Infrastructure Provider down'
        self.prerequisite_view.toolbar.configuration.item_select(item_title)


@navigator.register(OpenstackInfraProvider, 'ScaleOut')
class ProviderScaleOut(CFMENavigateStep):
    VIEW = ProviderScaleOutView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        item_title = 'Scale this Infrastructure Provider'
        self.prerequisite_view.toolbar.configuration.item_select(item_title)
