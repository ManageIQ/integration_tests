"""Provisioning-related forms and domain classes.

"""
from collections import OrderedDict
from cfme.services import requests
from cfme.fixtures import pytest_selenium as sel
from cfme import web_ui as ui
from cfme.web_ui.menu import nav
from cfme.web_ui import accordion, tabstrip, toolbar, paginator
from utils.update import Updateable
from utils.wait import wait_for

template_select_form = ui.Form(
    fields=[
        ('template_table', ui.Table('//div[@id="pre_prov_div"]/fieldset/table')),
        ('continue_button', '//img[@title="Continue"]'),
        ('cancel_button', '//img[@title="Continue"]')
    ]
)


def select_security_group(sg):
    '''Workaround for select box that is immediately replaced by the same
       select box no matter what selenium clicks on (but works fine
       manually).  For now only selects one item even though it's a
       multiselect.

    '''
    val = sel.get_attribute("//select[@id='environment__security_groups']/option[.='%s']" %
                            sg, 'value')
    sel.browser().execute_script(
        "$j('#environment__security_groups').val('%s');"
        "$j.ajax({type: 'POST', url: '/miq_request/prov_field_changed/new',"
        " data: {'environment__security_groups':'%s'}})" % (val, val))
    sel.wait_for_ajax()
    sel.sleep(1)


provisioning_form = tabstrip.TabStripForm(
    fields=[
        ('submit_button', '//*[@id="form_buttons"]/li[1]/img'),
        ('cancel_button', '//*[@id="form_buttons"]/li[2]/img')
    ],
    tab_fields=OrderedDict([
        ('Request', [
            ('email', '//input[@name="requester__owner_email"]'),
            ('first_name', '//input[@id="requester__owner_first_name"]'),
            ('last_name', '//input[@id="requester__owner_last_name"]'),
            ('notes', '//textarea[@id="requester__request_notes"]'),
            ('manager_name', '//input[@id="requester__owner_manager"]')
        ]),
        ('Purpose', [
            ('apply_tags', ui.Tree('//div[@id="all_tags_treebox"]//table'))
        ]),
        ('Catalog', [
            ('num_instances', ui.Select('//select[@id="service__number_of_vms"]')),
            ('instance_name', '//input[@name="service__vm_name"]'),
            ('instance_description', '//textarea[@id="service__vm_description"]'),
            ('catalog_name', ui.Table('//div[@id="prov_vm_div"]/table')),
        ]),
        ('Environment', [
            ('automatic_placement', '//input[@id="environment__placement_auto"]'),
            ('availability_zone',
                ui.Select('//select[@id="environment__placement_availability_zone"]')),
            ('security_groups', select_security_group),
            ('public_ip_address', ui.Select('//select[@id="environment__floating_ip_address"]')),
        ]),
        ('Properties', [
            ('instance_type', ui.Select('//select[@id="hardware__instance_type"]')),
            ('guest_keypair', ui.Select('//select[@id="hardware__guest_access_key_pair"]')),
            ('hardware_monitoring', ui.Select('//select[@id="hardware__monitoring"]')),
        ]),
        ('Customize', [
            ('specification', ui.Select('//select[@id="customize__sysprep_enabled"]')),
            ('specification_name', ui.Table('//div[@id="prov_vc_div"]/table')),
            ('computer_name', '//input[@id="customize__linux_host_name"]'),
            ('domain_name', '//input[@id="customize__linux_domain_name"]'),
            ('dns_servers', '//input[@id="customize__dns_servers"]'),
            ('dns_suffixes', '//input[@id="customize__dns_suffixes"]'),
        ]),
        ('Schedule', [
            ('schedule_type', ui.Radio('schedule__schedule_type')),
            ('provision_date', ui.Calendar('miq_date_1')),
            ('provision_start_hour', ui.Select('//select[@id="start_hour"]')),
            ('provision_start_min', ui.Select('//select[@id="start_min"]')),
            ('power_on', '//input[@id="schedule__vm_auto_start"]'),
            ('retirement', ui.Select('//select[@id="schedule__retirement"]')),
            ('retirement_warning', ui.Select('//select[@id="schedule__retirement_warn"]')),
        ])
    ])
)

instances_by_provider_tree = ui.Tree("//ul[@class='dynatree-container']")


# Nav targets and helpers
def _nav_to_provision_form(context):
    toolbar.select('Lifecycle', 'Provision Instances')
    provider = context['provider']
    template_name = context['template'].name

    template = template_select_form.template_table.find_row_by_cells({
        'Name': template_name,
        'Provider': provider.name
    })
    if template:
        sel.click(template)
        sel.click(template_select_form.continue_button)
    else:
        # Better exception?
        raise ValueError('Navigation failed: Unable to find template "%s" for provider "%s"' %
            (template_name, provider.name))

nav.add_branch(
    'clouds_instances',
    {
        'clouds_instances_by_provider':
        [nav.partial(accordion.click, 'Instances by Provider'),
         {'clouds_all_instances':
          [lambda _: instances_by_provider_tree.click_path('Instances by Provider'),  # select root
           {'clouds_provision_instances': lambda c: _nav_to_provision_form(c),
            'clouds_instance':
            lambda ctx: paginator.click_element(ui.Quadicon(ctx['instance'].name, 'instance'))}]}]})


class Template(object):
    def __init__(self, name):
        self.name = name


class Instance(Updateable):
    '''Represents an instance (or vm) in CFME.

       * provider_mgmt should be those returned by utils.mgmt_system.provider_factory
       * security_groups should be a list (currently only one is supported)
       * provider should be an instance of cfme.cloud.provider.Provider
       * template should be an instance of Template
    '''

    def __init__(self, email=None, first_name=None, last_name=None, notes=None, name=None,
                 instance_type=None, availability_zone=None, security_groups=None,
                 provider=None, template=None, provider_mgmt=None, guest_keypair=None):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.notes = notes
        self.name = name
        self.instance_type = instance_type
        self.availability_zone = availability_zone
        self.security_groups = security_groups
        self.provider = provider
        self.template = template
        self.provider_mgmt = provider_mgmt
        self.guest_keypair = guest_keypair

    def create(self):
        '''Creates an instance with the given properties'''
        sel.force_navigate('clouds_provision_instances', context={
            'provider': self.provider,
            'template': self.template,
        })
        ui.fill(provisioning_form, {
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'notes': self.notes,
            'instance_name': self.name,
            'instance_type': self.instance_type,
            'guest_keypair': self.guest_keypair,
            'availability_zone': self.availability_zone,
            'security_groups': self.security_groups[0],  # not supporting multiselect now,
                                                         # just take first value
        }, action=provisioning_form.submit_button)

        row_description = 'Provision from [%s] to [%s]' % (self.template.name, self.name)
        cells = {'Description': row_description}
        row, __ = wait_for(requests.wait_for_request, [cells],
                           fail_func=requests.reload, num_sec=600, delay=20)
        assert row.last_message.text == 'VM Provisioned Successfully'

    def power(self, on=True, cancel=False):
        sel.force_navigate('clouds_instance', context={'instance': self})
        toolbar.select("Power", "Start" if on else "Stop", invokes_alert=True)
        sel.handle_alert(cancel)
        if not cancel:
            wait_for(self.provider_mgmt.is_vm_state,
                 [self.name, self.provider_mgmt.states['running' if on else 'stopped']])

    def start(self):
        self.power(on=True)

    def stop(self):
        self.power(on=False)

    def terminate(self, cancel=False):
        sel.force_navigate('clouds_instance', context={'instance': self})
        toolbar.select("Power", "Terminate", invokes_alert=True)
        sel.handle_alert(cancel)
        if not cancel:
            wait_for(self.provider_mgmt.is_vm_state,
                     [self.name, self.provider_mgmt.states['deleted']])

    def delete(self, cancel=False):
        sel.force_navigate('clouds_instance', context={'instance': self})
        toolbar.select("Configuration", "Remove from the VMDB", invokes_alert=True)
        sel.handle_alert(cancel=cancel)
