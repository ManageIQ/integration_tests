import attr
from widgetastic.exceptions import NoSuchElementException
from wrapanapi.systems import VMWareSystem

from cfme.common.candu_views import VMUtilizationView
from cfme.common.provider import DefaultEndpoint
from cfme.common.provider import DefaultEndpointForm
from cfme.exceptions import ItemNotFound
from cfme.infrastructure.provider import InfraProvider
from cfme.services.catalogs.catalog_items import VMwareCatalogItem
from widgetastic_manageiq import LineChart


class VirtualCenterEndpoint(DefaultEndpoint):
    pass


class VirtualCenterEndpointForm(DefaultEndpointForm):
    pass


class VirtualCenterVMUtilizationView(VMUtilizationView):
    """A VM Utilization view for virtual center providers"""
    vm_cpu = LineChart(id='miq_chart_parent_candu_0')
    vm_cpu_state = LineChart(id='miq_chart_parent_candu_1')
    vm_memory = LineChart(id='miq_chart_parent_candu_2')
    vm_disk = LineChart(id='miq_chart_parent_candu_3')
    vm_network = LineChart(id='miq_chart_parent_candu_4')


@attr.s(cmp=False)
class VMwareProvider(InfraProvider):
    catalog_item_type = VMwareCatalogItem
    vm_utilization_view = VirtualCenterVMUtilizationView
    type_name = "virtualcenter"
    mgmt_class = VMWareSystem
    db_types = ["Vmware::InfraManager"]
    endpoints_form = VirtualCenterEndpointForm
    ems_pretty_name = 'VMware vCenter'
    discover_dict = {"vmware": True}
    settings_key = 'ems_vmware'
    # xpath locators for elements, to be used by selenium
    _console_connection_status_element = '//*[@id="connection-status"]|//*[@id="noVNC_status"]'
    _canvas_element = ('(//*[@id="remote-console" or @id="wmksContainer"]/canvas|'
        '//*[@id="noVNC_canvas"])')
    _ctrl_alt_del_xpath = '(//*[@id="ctrlaltdel"]|//*[@id="sendCtrlAltDelButton"])'
    _fullscreen_xpath = '//*[@id="fullscreen"]'
    bad_credentials_error_msg = 'Cannot complete login due to an incorrect user name or password.'
    log_name = 'vim'

    ems_events = [
        ('vm_create', {'event_type': 'VmDeployedEvent', 'dest_vm_or_template_id': None}),
        ('vm_stop', {'event_type': 'VmPoweredOffEvent', 'vm_or_template_id': None}),
        ('vm_start', {'event_type': 'VmPoweredOnEvent', 'vm_or_template_id': None}),
        ('vm_delete', {'event_type': 'VmRemovedEvent', 'vm_or_template_id': None})
    ]

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines """
        # Called within a dictionary update. Since we want to remove key/value pairs, return the
        # entire dictionary
        deploy_args.pop('username', None)
        deploy_args.pop('password', None)
        if "allowed_datastores" not in deploy_args and "allowed_datastores" in self.data:
            deploy_args['allowed_datastores'] = self.data['allowed_datastores']

        return deploy_args

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        appliance = appliance if appliance is not None else cls.appliance
        endpoint = VirtualCenterEndpoint(**prov_config['endpoints']['default'])

        if prov_config.get('discovery_range'):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')
        return appliance.collections.infra_providers.instantiate(
            prov_class=cls,
            name=prov_config['name'],
            endpoints={endpoint.name: endpoint},
            zone=prov_config['server_zone'],
            key=prov_key,
            start_ip=start_ip,
            end_ip=end_ip)

    @property
    def view_value_mapping(self):
        return dict(name=self.name, prov_type='VMware vCenter')

    # Following methods will only work if the remote console window is open
    # and if selenium focused on it. These will not work if the selenium is
    # focused on Appliance window.
    def _try_element_lookup(self, xpath):
        try:
            return self.appliance.browser.widgetastic.selenium.find_element_by_xpath(xpath)
        except NoSuchElementException:
            raise ItemNotFound("Element not found on screen, is current focus on console window?")

    def get_console_connection_status(self):
        return self._try_element_lookup(self._console_connection_status_element).text

    def get_remote_console_canvas(self):
        return self._try_element_lookup(self._canvas_element).text

    def get_console_ctrl_alt_del_btn(self):
        return self._try_element_lookup(self._ctrl_alt_del_xpath).text

    def get_console_fullscreen_btn(self):
        return self._try_element_lookup(self._fullscreen_xpath).text
