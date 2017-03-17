""" A model of an Infrastructure Provider in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Providers pages.
:var discover_form: A :py:class:`cfme.web_ui.Form` object describing the discover form.
:var properties_form: A :py:class:`cfme.web_ui.Form` object describing the main add form.
:var default_form: A :py:class:`cfme.web_ui.Form` object describing the default credentials form.
:var candu_form: A :py:class:`cfme.web_ui.Form` object describing the C&U credentials form.
"""
from functools import partial
from navmazing import NavigateToSibling, NavigateToObject
from widgetastic.widget import View, Text, FileInput
from cached_property import cached_property

from cfme import BaseLoggedInPage
from cfme.base.ui import Server
from cfme.common.provider import CloudInfraProvider
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.host import Host
from cfme.infrastructure.cluster import Cluster
from cfme.web_ui import (
    Region, Quadicon, Form, CheckboxTree, fill, form_buttons,
    AngularSelect, toolbar as tb, Radio, InfoBlock, match_location, paginator, BootstrapSwitch
)
from cfme.web_ui.form_buttons import FormButton
from cfme.web_ui.tabstrip import TabStripForm
from utils import conf, version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.log import logger
from utils.pretty import Pretty
from utils.varmeth import variable
from utils.wait import wait_for
from widgetastic_manageiq import (PaginationPane,
                                  BreadCrumb,
                                  Checkbox,
                                  SummaryTable,
                                  ManageIQTree,
                                  Button,
                                  TimelinesView,
                                  RadioGroup)
from widgetastic_patternfly import Input, BootstrapSelect, Tab, Dropdown
from .widgetastic_views import (ProviderEntities,
                                ProviderSideBar,
                                ProviderToolBar,
                                DetailsProviderToolBar)


details_page = Region(infoblock_type='detail')
match_page = partial(match_location, controller='ems_infra', title='Infrastructure Providers')

# Forms
discover_form = Form(
    fields=[
        ('rhevm_chk', Input("discover_type_rhevm")),
        ('vmware_chk', Input("discover_type_virtualcenter")),
        ('scvmm_chk', Input("discover_type_scvmm")),
        ('from_0', Input("from_first")),
        ('from_1', Input("from_second")),
        ('from_2', Input("from_third")),
        ('from_3', Input("from_fourth")),
        ('to_3', Input("to_fourth")),
        ('start_button', FormButton("Start the Host Discovery"))
    ])


properties_form = TabStripForm(
    fields=[
        ('type_select', AngularSelect("emstype")),
        ('name_text', Input("name")),
        ("api_version", AngularSelect("api_version")),
    ],
    tab_fields={
        "Default": [
            ('hostname_text', Input("default_hostname")),
            ('api_port', Input("default_api_port")),
            ('sec_protocol', AngularSelect("default_security_protocol", exact=True)),
            ('verify_tls_switch', BootstrapSwitch(input_id="default_tls_verify")),
            ('ca_certs', Input('default_tls_ca_certs')),
        ],
        "Events": [
            ('event_selection', Radio('event_stream_selection')),
            ('amqp_hostname_text', Input("amqp_hostname")),
            ('amqp_api_port', Input("amqp_api_port")),
            ('amqp_sec_protocol', AngularSelect("amqp_security_protocol", exact=True)),
        ],
        "C & U Database": [
            ('candu_hostname_text', Input("metrics_hostname")),
            ('acandu_api_port', Input("metrics_api_port")),
        ]
    })

prop_region = Region(locators={'properties_form': properties_form})

manage_policies_tree = CheckboxTree("//div[@id='protect_treebox']/ul")

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')
mon_btn = partial(tb.select, 'Monitoring')


class InfraProvidersView(BaseLoggedInPage):
    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and \
            self.entities.title.text == 'Infrastructure Providers'

    @View.nested
    class toolbar(ProviderToolBar):  # NOQA
        pass

    @View.nested
    class sidebar(ProviderSideBar):  # NOQA
        pass

    @View.nested
    class entities(ProviderEntities):  # NOQA
        pass

    @View.nested
    class paginator(PaginationPane):  # NOQA
        pass


class InfraProviderDetailsView(BaseLoggedInPage):
    @View.nested
    class toolbar(DetailsProviderToolBar):  # NOQA
        pass

    title = Text('//div[@id="main-content"]//h1')
    breadcrumb = BreadCrumb(locator='//ol[@class="breadcrumb"]')

    properties = SummaryTable(title="Properties")
    status = SummaryTable(title="Status")
    relationships = SummaryTable(title="Relationships")
    overview = SummaryTable(title="Overview")
    smart_management = SummaryTable(title="Smart Management")


class InfraProvidersDiscoverView(BaseLoggedInPage):
    vcenter = Checkbox('discover_type_virtualcenter')
    mscvmm = Checkbox('discover_type_scvmm')
    rhevm = Checkbox('discover_type_rhevm')

    from_ip1 = Input('from_first')
    from_ip2 = Input('from_second')
    from_ip3 = Input('from_third')
    from_ip4 = Input('from_fourth')
    to_ip4 = Input('to_fourth')

    start = Button('Start')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and \
            match_page(summary='Infrastructure Providers Discovery')


class DefaultEndpointForm(View):
    hostname = Input('default_hostname')
    username = Input('default_userid')
    password = Input('default_password')
    confirm_password = Input('default_verify')

    validate = Button('Validate')


class SCVMMEndpointForm(DefaultEndpointForm):
    security_protocol = BootstrapSelect(id='default_security_protocol')
    realm = Input('realm')  # appears when Kerberos is chosen in security_protocol


class VirtualCenterEndpointForm(DefaultEndpointForm):
    pass


class RHEVMEndpointForm(View):
    @View.nested
    class default(Tab, DefaultEndpointForm):  # NOQA
        TAB_NAME = 'Default'
        api_port = Input('default_api_port')

    @View.nested
    class database(Tab):  # NOQA
        TAB_NAME = 'C & U Database'
        hostname = Input('metrics_hostname')
        api_port = Input('metrics_api_port')
        database_name = Input('metrics_database_name')
        username = Input('metrics_userid')
        password = Input('metrics_password')
        confirm_password = Input('metrics_verify')

        validate = Button('Validate')


class OpenStackInfraEndpointForm(View):
    @View.nested
    class default(Tab, DefaultEndpointForm):  # NOQA
        TAB_NAME = 'Default'
        api_port = Input('default_api_port')
        security_protocol = BootstrapSelect('default_security_protocol')

    @View.nested
    class events(Tab):
        TAB_NAME = 'Events'
        event_stream = RadioGroup(locator='//div[@id="amqp"]')
        # below controls which appear only if amqp is chosen
        hostname = Input('amqp_hostname')
        api_port = Input('amqp_api_port')
        security_protocol = BootstrapSelect('amqp_security_protocol')

        username = Input('amqp_userid')
        password = Input('amqp_password')
        confirm_password = Input('amqp_verify')

        validate = Button('Validate')

    @View.nested
    class rsa_keypair(Tab):
        TAB_NAME = 'RSA key pair'

        username = Input('ssh_keypair_userid')
        private_key = FileInput(locator='.//input[@id="ssh_keypair_password"]')


class InfraProvidersAddView(BaseLoggedInPage):
    title = Text('//div[@id="main-content"]//h1')
    name = Input('name')
    prov_type = BootstrapSelect(id='emstype')
    api_version = BootstrapSelect(id='api_version')  # only for OpenStack
    zone = Input('zone')
    add = Button('Add')
    cancel = Button('Cancel')

    @View.nested
    class endpoints(View):  # NOQA
        # this is switchable view that gets replaced this concrete view.
        # it gets changed according to currently chosen provider type every time
        # when it is accessed
        pass

    def __getattribute__(self, item):
        if item == 'endpoints':
            if self.prov_type.selected_option == 'Microsoft System Center VMM':
                return SCVMMEndpointForm(parent=self)

            elif self.prov_type.selected_option == 'VMware vCenter':
                return VirtualCenterEndpointForm(parent=self)

            elif self.prov_type.selected_option == 'Red Hat Virtualization Manager':
                return RHEVMEndpointForm(parent=self)

            elif self.prov_type.selected_option == 'OpenStack Platform Director':
                return OpenStackInfraEndpointForm(parent=self)

            else:
                raise Exception('The form for provider with such name '
                                'is absent: {}'.format(self.prov_type.text))
        else:
            return super(InfraProvidersAddView, self).__getattribute__(item)

    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and \
            self.title.text == 'Add New Infrastructure Provider'


class InfraProvidersManagePoliciesView(BaseLoggedInPage):
    policies = ManageIQTree('protectbox')
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


class InfraProvidersEditTagsView(BaseLoggedInPage):
    # todo: to add table and assignment controls

    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


class InfraProviderTimelinesView(TimelinesView, BaseLoggedInPage):
    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] \
            and TimelinesView.is_displayed


class InfraProviderCollection(Navigatable):
    """Collection object for the :py:class:`InfraProvider`."""
    def create(self, name=None, credentials=None, key=None, zone=None, provider_data=None,
               cancel=False):
        pass

    def all(self):
        pass

    def delete(self, name):
        pass


class InfraProvider(Pretty, CloudInfraProvider):
    """
    Abstract model of an infrastructure provider in cfme. See VMwareProvider or RHEVMProvider.

    Args:
        name: Name of the provider.
        details: a details record (see VMwareDetails, RHEVMDetails inner class).
        credentials (:py:class:`Credential`): see Credential inner class.
        key: The CFME key of the provider in the yaml.
        candu: C&U credentials if this is a RHEVMDetails class.

    Usage:

        myprov = VMwareProvider(name='foo',
                             region='us-west-1',
                             credentials=Provider.Credential(principal='admin', secret='foobar'))
        myprov.create()

    """
    provider_types = {}
    in_version = (version.LOWEST, version.LATEST)
    category = "infra"
    pretty_attrs = ['name', 'key', 'zone']
    STATS_TO_MATCH = ['num_template', 'num_vm', 'num_datastore', 'num_host', 'num_cluster']
    string_name = "Infrastructure"
    page_name = "infrastructure"
    templates_destination_name = "Templates"
    quad_name = "infra_prov"
    _properties_region = prop_region  # This will get resolved in common to a real form
    db_types = ["InfraManager"]
    add_provider_button = form_buttons.add
    save_button = form_buttons.angular_save

    def __init__(
            self, name=None, credentials=None, key=None, zone=None, provider_data=None,
            appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        if not credentials:
            credentials = {}
        self.name = name
        self.credentials = credentials
        self.key = key
        self.provider_data = provider_data
        self.zone = zone
        self.template_name = "Templates"

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name')}

    @cached_property
    def vm_name(self):
        return version.pick({
            version.LOWEST: "VMs and Instances",
            '5.7.1': "Virtual Machines"})

    @variable(alias='db')
    def num_datastore(self):
        storage_table_name = version.pick({version.LOWEST: 'hosts_storages',
                                           '5.5.0.8': 'host_storages'})
        """ Returns the providers number of templates, as shown on the Details page."""

        results = list(self.appliance.db.engine.execute(
            'SELECT DISTINCT storages.name, hosts.ems_id '
            'FROM ext_management_systems, hosts, storages, {} '
            'WHERE hosts.id={}.host_id AND '
            'storages.id={}.storage_id AND '
            'hosts.ems_id=ext_management_systems.id AND '
            'ext_management_systems.name=\'{}\''.format(storage_table_name,
                                                        storage_table_name, storage_table_name,
                                                        self.name)))
        return len(results)

    @num_datastore.variant('ui')
    def num_datastore_ui(self):
            return int(self.get_detail("Relationships", "Datastores"))

    @variable(alias='rest')
    def num_host(self):
        provider = self.appliance.rest_api.collections.providers.find_by(name=self.name)[0]
        num_host = 0
        for host in self.appliance.rest_api.collections.hosts:
            if host['ems_id'] == provider.id:
                num_host += 1
        return num_host

    @num_host.variant('db')
    def num_host_db(self):
        ext_management_systems = self.appliance.db["ext_management_systems"]
        hosts = self.appliance.db["hosts"]
        hostlist = list(self.appliance.db.session.query(hosts.name)
                        .join(ext_management_systems, hosts.ems_id == ext_management_systems.id)
                        .filter(ext_management_systems.name == self.name))
        return len(hostlist)

    @num_host.variant('ui')
    def num_host_ui(self):
        host_src = "host-"
        node_src = "node-"

        try:
            num = int(self.get_detail("Relationships", host_src, use_icon=True))
        except sel.NoSuchElementException:
            logger.error("Couldn't find number of hosts using key [Hosts] trying Nodes")
            num = int(self.get_detail("Relationships", node_src, use_icon=True))
        return num

    @variable(alias='rest')
    def num_cluster(self):
        provider = self.appliance.rest_api.collections.providers.find_by(name=self.name)[0]
        num_cluster = 0
        for cluster in self.appliance.rest_api.collections.clusters:
            if cluster['ems_id'] == provider.id:
                num_cluster += 1
        return num_cluster

    @num_cluster.variant('db')
    def num_cluster_db(self):
        """ Returns the providers number of templates, as shown on the Details page."""
        ext_management_systems = self.appliance.db["ext_management_systems"]
        clusters = self.appliance.db["ems_clusters"]
        clulist = list(self.appliance.db.session.query(clusters.name)
                       .join(ext_management_systems,
                             clusters.ems_id == ext_management_systems.id)
                       .filter(ext_management_systems.name == self.name))
        return len(clulist)

    @num_cluster.variant('ui')
    def num_cluster_ui(self):
        return int(self.get_detail("Relationships", "cluster-", use_icon=True))

    def discover(self):
        """
        Begins provider discovery from a provider instance

        Usage:
            discover_from_config(utils.providers.get_crud('rhevm'))
        """
        from virtualcenter import VMwareProvider
        from rhevm import RHEVMProvider
        from scvmm import SCVMMProvider
        vmware = isinstance(self, VMwareProvider)
        rhevm = isinstance(self, RHEVMProvider)
        scvmm = isinstance(self, SCVMMProvider)
        discover(rhevm, vmware, scvmm, cancel=False, start_ip=self.start_ip,
                 end_ip=self.end_ip)

    @property
    def id(self):
        """
        returns current provider id using rest api
        """
        return self.appliance.rest_api.collections.providers.find_by(name=self.name)[0].id

    @property
    def hosts(self):
        """Returns list of :py:class:`cfme.infrastructure.host.Host` that should belong to this
        provider according to the YAML
        """
        result = []
        for host in self.get_yaml_data().get("hosts", []):
            creds = conf.credentials.get(host["credentials"], {})
            cred = Host.Credential(
                principal=creds["username"],
                secret=creds["password"],
                verify_secret=creds["password"],
            )
            result.append(Host(name=host["name"],
                               credentials=cred,
                               provider=self))
        return result

    def get_clusters(self):
        """returns the list of clusters belonging to the provider"""
        web_clusters = []
        navigate_to(self, 'Details')
        sel.click(InfoBlock.element('Relationships', 'Clusters'))
        icons = Quadicon.all(qtype='cluster')
        for icon in icons:
            web_clusters.append(Cluster(icon.name, self))
        return web_clusters


@navigator.register(Server, 'InfraProviders')
@navigator.register(InfraProvider, 'All')
class All(CFMENavigateStep):
    VIEW = InfraProvidersView
    prerequisite = NavigateToObject(Server, 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Providers')

    def resetter(self):
        # Reset view and selection
        tb = self.view.toolbar
        paginator = self.view.paginator
        if 'Grid View' not in tb.view_selector.selected:
            tb.view_selector.select('Grid View')
        if paginator.exists:
            paginator.check_all()
            paginator.uncheck_all()


@navigator.register(InfraProvider, 'Add')
class Add(CFMENavigateStep):
    VIEW = InfraProvidersAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg = self.prerequisite_view.toolbar.configuration
        cfg.item_select('Add a New Infrastructure Provider')


@navigator.register(InfraProvider, 'Discover')
class Discover(CFMENavigateStep):
    VIEW = InfraProvidersDiscoverView
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn('Discover Infrastructure Providers')


@navigator.register(InfraProvider, 'Details')
class Details(CFMENavigateStep):
    VIEW = InfraProviderDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))

    def resetter(self):
        # Reset view and selection
        if tb.exists("Summary View"):
            tb.select("Summary View")


@navigator.register(InfraProvider, 'ManagePolicies')
class ManagePolicies(CFMENavigateStep):
    VIEW = InfraProvidersManagePoliciesView
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        pol_btn('Manage Policies')


@navigator.register(InfraProvider, 'ManagePoliciesFromDetails')
class ManagePoliciesFromDetails(CFMENavigateStep):
    VIEW = InfraProvidersManagePoliciesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Manage Policies')


@navigator.register(InfraProvider, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = InfraProvidersEditTagsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        pol_btn('Edit Tags')


@navigator.register(InfraProvider, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    VIEW = InfraProvidersEditTagsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Edit Tags')


@navigator.register(InfraProvider, 'Edit')
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        cfg_btn('Edit Selected Infrastructure Providers')


@navigator.register(InfraProvider, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = InfraProviderTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        mon_btn('Timelines')


@navigator.register(InfraProvider, 'Instances')
class Instances(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return match_page(summary='{} (All VMs)'.format(self.obj.name))

    def step(self, *args, **kwargs):
        sel.click(InfoBlock.element('Relationships', 'VMs and Instances'))


@navigator.register(InfraProvider, 'Templates')
class Templates(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return match_page(summary='{} (All Templates)'.format(self.obj.name))

    def step(self, *args, **kwargs):
        sel.click(InfoBlock.element('Relationships', 'Templates'))


def get_all_providers(do_not_navigate=False):
    """Returns list of all providers"""
    if not do_not_navigate:
        navigate_to(InfraProvider, 'All')
    providers = set([])
    link_marker = "ems_infra"
    for page in paginator.pages():
        for title in sel.elements("//div[@id='quadicon']/../../../tr/td/a[contains(@href,"
                "'{}/show')]".format(link_marker)):
            providers.add(sel.get_attribute(title, "title"))
    return providers


def discover(rhevm=False, vmware=False, scvmm=False, cancel=False, start_ip=None, end_ip=None):
    """
    Discover infrastructure providers. Note: only starts discovery, doesn't
    wait for it to finish.

    Args:
        rhevm: Whether to scan for RHEVM providers
        vmware: Whether to scan for VMware providers
        scvmm: Whether to scan for SCVMM providers
        cancel:  Whether to cancel out of the discover UI.
        start_ip: String start of the IP range for discovery
        end_ip: String end of the IP range for discovery
    """
    navigate_to(InfraProvider, 'Discover')
    form_data = {}
    if rhevm:
        form_data.update({'rhevm_chk': True})
    if vmware:
        form_data.update({'vmware_chk': True})
    if scvmm:
        form_data.update({'scvmm_chk': True})

    if start_ip:
        for idx, octet in enumerate(start_ip.split('.')):
            key = 'from_%i' % idx
            form_data.update({key: octet})
    if end_ip:
        end_octet = end_ip.split('.')[-1]
        form_data.update({'to_3': end_octet})

    fill(discover_form, form_data,
         action=form_buttons.cancel if cancel else discover_form.start_button,
         action_always=True)


def wait_for_a_provider():
    navigate_to(InfraProvider, 'All')
    logger.info('Waiting for a provider to appear...')
    wait_for(paginator.rec_total, fail_condition=None, message="Wait for any provider to appear",
             num_sec=1000, fail_func=sel.refresh)
