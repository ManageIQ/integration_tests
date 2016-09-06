""" A model of a Cloud Provider in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Providers pages.
:var discover_form: A :py:class:`cfme.web_ui.Form` object describing the discover form.
:var properties_form: A :py:class:`cfme.web_ui.Form` object describing the main add form.
:var default_form: A :py:class:`cfme.web_ui.Form` object describing the default credentials form.
:var amqp_form: A :py:class:`cfme.web_ui.Form` object describing the AMQP credentials form.
"""

from functools import partial
from navmazing import NavigateToSibling

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import form_buttons
from cfme.web_ui import toolbar as tb
from cfme.common.provider import CloudInfraProvider, import_all_modules_of
from cfme.web_ui.menu import nav
from cfme.web_ui import Region, Quadicon, Form, Select, fill, paginator, AngularSelect, Radio
from cfme.web_ui import Input
from cfme.web_ui.tabstrip import TabStripForm
from utils.appliance import get_or_create_current_appliance, CurrentAppliance
from utils.appliance.endpoints.ui import navigate, CFMENavigateStep
from utils.log import logger
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
        ('azure_subscription_id', Input("subscription"), {'appeared_in', '5.6'}),
        ('api_version', AngularSelect("api_version"), {"appeared_in": "5.5"}),
        ('sec_protocol', AngularSelect("security_protocol", exact=True), {"appeared_in": "5.5"}),
        ('infra_provider', {
            version.LOWEST: None,
            "5.4": Select("select#provider_id"),
            "5.5": AngularSelect("provider_id")}),
    ])

properties_form_56 = TabStripForm(
    fields=[
        ('type_select', AngularSelect("ems_type")),
        ('name_text', Input("name")),
        ('region_select', {
            version.LOWEST: AngularSelect("ems_region"),
            '5.7': AngularSelect('provider_region')}),
        ('google_region_select', AngularSelect("ems_preferred_region")),
        ('api_version', AngularSelect("ems_api_version")),
        ('infra_provider', AngularSelect("ems_infra_provider_id")),
        ('google_project_text', Input("project")),
        ('azure_tenant_id', Input("azure_tenant_id")),
        ('azure_subscription_id', Input("subscription")),
    ],
    tab_fields={
        "Default": [
            ('hostname_text', Input("default_hostname")),
            ('api_port', Input("default_api_port")),
            ('sec_protocol', AngularSelect("default_security_protocol", exact=True)),
        ],
        "Events": [
            ('event_selection', Radio('event_stream_selection')),
            ('amqp_hostname_text', Input("amqp_hostname")),
            ('amqp_api_port', Input("amqp_api_port")),
            ('amqp_sec_protocol', AngularSelect("amqp_security_protocol", exact=True)),
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
    type_tclass = "cloud"
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
    appliance = CurrentAppliance()

    def __init__(self, name=None, credentials=None, zone=None, key=None, appliance=None):
        self.appliance = appliance or get_or_create_current_appliance()
        if not credentials:
            credentials = {}
        self.name = name
        self.credentials = credentials
        self.zone = zone
        self.key = key

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name')}


@navigate.register(Provider, 'All')
class All(CFMENavigateStep):
    def prerequisite(self):
        self.navigate_obj.navigate(self.obj.appliance, 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Clouds', 'Providers')(None)


@navigate.register(Provider, 'Add')
class New(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn('Add a New Cloud Provider')


@navigate.register(Provider)
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, 'cloud_prov'))


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

import_all_modules_of('cfme.cloud.provider')
