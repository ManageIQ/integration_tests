from widgetastic_patternfly import Button, BootstrapSwitch, BootstrapSelect
from widgetastic.widget import TextInput, Text

from cfme.base.login import BaseLoggedInPage


class AddNewNetworkRouterView(BaseLoggedInPage):
    """ Represents whole All NetworkProviders page """
    name_field = TextInput(name='name')
    provider_dropdown = BootstrapSelect(id='ems_id')
    external_gateway = BootstrapSwitch(id='network_router_external_gateway')
    add = Button('Add')
    cancel = Button('Cancel')
    tenant_select = BootstrapSelect(locator='//*[@id="form_div"]/div[3]/div/div/div/button/..')
    net_select = BootstrapSelect(locator='//*[@id="form_div"]/div[2]/'
                                         'div[4]/div[2]/div/div/button/..')
    source_nat = BootstrapSwitch(id='network_router_enable_snat')
    subnet_select = BootstrapSelect(locator='//*[@id="form_div"]/div[2]/'
                                    'div[4]/div[3]/div/div/div/button/..')

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Network Routers'] and
                self.title.text == 'Add New Router')


class AddNewCloudNetworkView(BaseLoggedInPage):
    """ Represents whole All NetworkProviders page """
    name_field = TextInput(name='name')
    provider_dropdown = BootstrapSelect(id='ems_id')
    tenant_select = BootstrapSelect(locator='//*[@id="form_div"]/div[3]/div/div/div/button/..')
    external_router = BootstrapSwitch(id='cloud_network_external_facing')
    administrative_state = BootstrapSwitch(id='cloud_network_enabled')
    shared = BootstrapSwitch(id='cloud_network_shared')
    add = Button('Add')
    cancel = Button('Cancel')
    provider_type = BootstrapSelect(locator='//*[@id="form_div"]/div[4]/div/div/div/button/..')

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Networks'] and
                self.title.text == 'Add New Cloud Network')


class AddNewSubnetView(BaseLoggedInPage):
    """ Represents whole All NetworkProviders page """
    title = Text('//div[@id="main-content"]//h1')

    provider_dropdown = BootstrapSelect(id='ems_id')
    name_field = TextInput(name='name')
    gateway = TextInput(name='gateway_ip')
    net_select = BootstrapSelect(locator='//*[@id="form_div"]/div[3]/div[1]/div/div/button/..')
    enable_dhcp = BootstrapSwitch(id='cloud_subnet_dhcp_enabled')
    ip_version = BootstrapSelect(id="network_protocol")
    subnet_cidr = TextInput(name='cidr')
    tenant_select = BootstrapSelect(locator='//*[@id="form_div"]/div[4]/div/div/div/button/..')
    add = Button('Add')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Subnets'] and
                self.title.text == 'Add New Subnet')


class AddNewSecurityGroupView(BaseLoggedInPage):
    """ Represents whole All NetworkProviders page """
    title = Text('//div[@id="main-content"]//h1')

    provider_dropdown = BootstrapSelect(id='ems_id')
    name_field = TextInput(name='name')
    description = TextInput(name='description')
    tenant_select = BootstrapSelect(locator='//*[@id="form_div"]/div[4]/div/div/div/button/..')
    add = Button('Add')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Security Groups'] and
                self.title.text == 'Add New Security Group')


class AddNewFloatingIPView(BaseLoggedInPage):
    """ Represents whole All NetworkProviders page """
    title = Text('//div[@id="main-content"]//h1')

    provider_dropdown = BootstrapSelect(id='ems_id')
    associated_port = TextInput(name='description')
    floating_ip = TextInput(name='name')
    external_network = BootstrapSelect(locator='//*[@id="form_div"]/div[2]/'
                                               'div[2]/div/div/button/..')
    tenant_select = BootstrapSelect(locator='//*[@id="form_div"]/div[4]/div/div/div/button/..')
    add = Button('Add')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Floating IPs'] and
                self.title.text == 'Add New Floating IP')
