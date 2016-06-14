""" A model of a Cloud Provider in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Providers pages.
:var discover_form: A :py:class:`cfme.web_ui.Form` object describing the discover form.
:var properties_form: A :py:class:`cfme.web_ui.Form` object describing the main add form.
:var default_form: A :py:class:`cfme.web_ui.Form` object describing the default credentials form.
:var amqp_form: A :py:class:`cfme.web_ui.Form` object describing the AMQP credentials form.
"""

from functools import partial

import cfme.fixtures.pytest_selenium as sel
from cfme.infrastructure.provider import OpenstackInfraProvider
from cfme.web_ui import form_buttons
from cfme.web_ui import toolbar as tb
from cfme.common.provider import CloudInfraProvider
from cfme.web_ui.menu import nav
from cfme.web_ui import Region, Quadicon, Form, Select, fill, paginator, AngularSelect, Radio
from cfme.web_ui import Input
from cfme.web_ui.tabstrip import TabStripForm
from utils.log import logger
from utils.providers import setup_provider_by_name
from utils.wait import wait_for
from utils import version, deferred_verpick
from utils.pretty import Pretty


# Forms
discover_form = Form(
    fields=[
        ('discover_select', AngularSelect("discover_type_selected"), {"appeared_in": "5.5"}),
        ('username', "#userid"),
        ('password', "#password"),
        ('password_verify', "#verify"),
        ('start_button', form_buttons.FormButton("Start the Host Discovery"))
    ])

properties_form_55 = Form(
    fields=[
        ('type_select', {version.LOWEST: Select('select#server_emstype'),
            '5.5': AngularSelect("emstype")}),
        ('azure_tenant_id', Input("azure_tenant_id")),
        ('name_text', Input("name")),
        ('azure_region_select', AngularSelect("provider_region")),
        ('hostname_text', Input("hostname")),
        ('ipaddress_text', Input("ipaddress"), {"removed_since": "5.4.0.0.15"}),
        ('region_select', {version.LOWEST: Select("select#provider_region"),
            "5.5": AngularSelect("provider_region")}),
        ('api_port', Input(
            {
                version.LOWEST: "port",
                "5.5": "api_port",
            }
        )),
        ('infra_provider', Input("provider_id")),
        ('subscription', Input("subscription")),
        ("api_version", AngularSelect("api_version"), {"appeared_in": "5.5"}),
        ('sec_protocol', AngularSelect("security_protocol"), {"appeared_in": "5.5"}),
        ('infra_provider', {
            version.LOWEST: None,
            "5.4": Select("select#provider_id"),
            "5.5": AngularSelect("provider_id")}),
    ])

properties_form_56 = TabStripForm(
    fields=[
        ('type_select', AngularSelect("ems_type")),
        ('name_text', Input("name")),
        ('region_select', AngularSelect("ems_region")),
        ('google_region_select', AngularSelect("ems_preferred_region")),
        ("api_version", AngularSelect("ems_api_version")),
        ('infra_provider', AngularSelect("ems_infra_provider_id")),
        ('google_project_text', Input("project")),
        ('azure_tenant_id', Input("azure_tenant_id")),
        ('azure_subscription_id', Input("subscription")),
        ('amazon_region_select', {version.LOWEST: Select("select#provider_region"),
            "5.5": AngularSelect("provider_region")}),
        ("api_version", AngularSelect("api_version")),
    ],
    tab_fields={
        "Default": [
            ('hostname_text', Input("default_hostname")),
            ('api_port', Input("default_api_port")),
            ('sec_protocol', AngularSelect("default_security_protocol")),
        ],
        "Events": [
            ('event_selection', Radio('event_stream_selection')),
            ('amqp_hostname_text', Input("amqp_hostname")),
            ('amqp_api_port', Input("amqp_api_port")),
            ('amqp_sec_protocol', AngularSelect("amqp_security_protocol")),
        ]
    })

prop_region = Region(
    locators={
        'properties_form': {
            version.LOWEST: properties_form_55,
            '5.6': properties_form_56,
        }
    }
)

details_page = Region(infoblock_type='detail')

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')
mon_btn = partial(tb.select, 'Monitoring')

nav.add_branch('clouds_providers',
               {'clouds_provider_new': lambda _: cfg_btn('Add a New Cloud Provider'),
                'clouds_provider_discover': lambda _: cfg_btn('Discover Cloud Providers'),
                'clouds_provider': [lambda ctx: sel.click(Quadicon(ctx['provider'].name,
                                                                  'cloud_prov')),
                                   {'clouds_provider_edit':
                                    lambda _: cfg_btn('Edit this Cloud Provider'),
                                    'clouds_provider_policy_assignment':
                                    lambda _: pol_btn('Manage Policies'),
                                    'cloud_provider_timelines':
                                    lambda _: mon_btn('Timelines')}]})


class Provider(Pretty, CloudInfraProvider):
    """
    Abstract model of a cloud provider in cfme. See EC2Provider or OpenStackProvider.

    Args:
        name: Name of the provider.
        details: a details record (see EC2Details, OpenStackDetails inner class).
        credentials (Credential): see Credential inner class.
        key: The CFME key of the provider in the yaml.

    Usage:

        myprov = EC2Provider(name='foo',
                             region='us-west-1',
                             credentials=Provider.Credential(principal='admin', secret='foobar'))
        myprov.create()

    """
    pretty_attrs = ['name', 'credentials', 'zone', 'key']
    STATS_TO_MATCH = ['num_template', 'num_vm']
    string_name = "Cloud"
    page_name = "clouds"
    instances_page_name = "clouds_instances_by_provider"
    templates_page_name = "clouds_images_by_provider"
    quad_name = "cloud_prov"
    vm_name = "Instances"
    template_name = "Images"
    _properties_region = prop_region  # This will get resolved in common to a real form
    # Specific Add button
    add_provider_button = deferred_verpick(
        {version.LOWEST: form_buttons.FormButton("Add this Cloud Provider"),
         '5.5': form_buttons.add})
    save_button = deferred_verpick(
        {version.LOWEST: form_buttons.save,
         '5.5': form_buttons.angular_save})

    def __init__(self, name=None, credentials=None, zone=None, key=None):
        if not credentials:
            credentials = {}
        self.name = name
        self.credentials = credentials
        self.zone = zone
        self.key = key

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name')}


class AzureProvider(Provider):
    def __init__(self, name=None, credentials=None, zone=None, key=None, region=None,
                 tenant_id=None, subscription_id=None):
        super(AzureProvider, self).__init__(name=name, credentials=credentials,
                                            zone=zone, key=key)
        self.region = region
        self.tenant_id = tenant_id
        self.subscription_id = subscription_id

    def _form_mapping(self, create=None, **kwargs):
        # Will still need to figure out where to put the tenant id.
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Azure',
                'region_select': kwargs.get('region'),
                'azure_tenant_id': kwargs.get('tenant_id'),
                'azure_subscription_id': kwargs.get('subscription_id')}


class EC2Provider(Provider):
    def __init__(self, name=None, credentials=None, zone=None, key=None, region=None):
        super(EC2Provider, self).__init__(name=name, credentials=credentials,
                                          zone=zone, key=key)
        self.region = region

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Amazon EC2',
                'region_select': sel.ByValue(kwargs.get('region'))}


class GCEProvider(Provider):
    def __init__(self, name=None, project=None, zone=None, region=None, credentials=None, key=None):
        super(GCEProvider, self).__init__(name=name, zone=zone, key=key, credentials=credentials)
        self.region = region
        self.project = project

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Google Compute Engine',
                'google_region_select': sel.ByValue(kwargs.get('region')),
                'google_project_text': kwargs.get('project')}


class OpenStackProvider(Provider):
    def __init__(self, name=None, credentials=None, zone=None, key=None, hostname=None,
                 ip_address=None, api_port=None, sec_protocol=None, amqp_sec_protocol=None,
                 infra_provider=None):
        super(OpenStackProvider, self).__init__(name=name, credentials=credentials,
                                                zone=zone, key=key)
        self.hostname = hostname
        self.ip_address = ip_address
        self.api_port = api_port
        self.infra_provider = infra_provider
        self.sec_protocol = sec_protocol
        self.amqp_sec_protocol = amqp_sec_protocol

    def create(self, *args, **kwargs):
        # Override the standard behaviour to actually create the underlying infra first.
        if self.infra_provider is not None:
            if isinstance(self.infra_provider, OpenstackInfraProvider):
                infra_provider_name = self.infra_provider.name
            else:
                infra_provider_name = str(self.infra_provider)
            setup_provider_by_name(
                infra_provider_name, validate=True, check_existing=True)
        return super(OpenStackProvider, self).create(*args, **kwargs)

    def _form_mapping(self, create=None, **kwargs):
        infra_provider = kwargs.get('infra_provider')
        if isinstance(infra_provider, OpenstackInfraProvider):
            infra_provider = infra_provider.name
        data_dict = {
            'name_text': kwargs.get('name'),
            'type_select': create and 'OpenStack',
            'hostname_text': kwargs.get('hostname'),
            'api_port': kwargs.get('api_port'),
            'ipaddress_text': kwargs.get('ip_address'),
            'sec_protocol': kwargs.get('sec_protocol'),
            'infra_provider': "---" if infra_provider is False else infra_provider}
        if 'amqp' in self.credentials:
            data_dict.update({
                'event_selection': 'amqp',
                'amqp_hostname_text': kwargs.get('hostname'),
                'amqp_api_port': kwargs.get('amqp_api_port', '5672'),
                'amqp_sec_protocol': kwargs.get('amqp_sec_protocol', "Non-SSL")
            })
        return data_dict


def get_all_providers(do_not_navigate=False):
    """Returns list of all providers"""
    if not do_not_navigate:
        sel.force_navigate('clouds_providers')
    providers = set([])
    link_marker = "ems_cloud"
    for page in paginator.pages():
        for title in sel.elements("//div[@id='quadicon']/../../../tr/td/a[contains(@href,"
                "'{}/show')]".format(link_marker)):
            providers.add(sel.get_attribute(title, "title"))
    return providers


def discover(credential, cancel=False, d_type="Amazon"):
    """
    Discover cloud providers. Note: only starts discovery, doesn't
    wait for it to finish.

    Args:
      credential (cfme.Credential):  Amazon discovery credentials.
      cancel (boolean):  Whether to cancel out of the discover UI.
    """
    sel.force_navigate('clouds_provider_discover')
    form_data = {'discover_select': d_type}
    if credential:
        form_data.update({'username': credential.principal,
                          'password': credential.secret,
                          'password_verify': credential.verify_secret})
    fill(discover_form, form_data,
         action=form_buttons.cancel if cancel else discover_form.start_button,
         action_always=True)


def wait_for_a_provider():
    sel.force_navigate('clouds_providers')
    logger.info('Waiting for a provider to appear...')
    wait_for(paginator.rec_total, fail_condition=None, message="Wait for any provider to appear",
             num_sec=1000, fail_func=sel.refresh)
