# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.infrastructure.provider.kubevirt import KubeVirtProvider
from cfme.provisioning import do_vm_provisioning
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.update import update


pytestmark = [
    pytest.mark.provider([KubeVirtProvider]),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture
def temp_vm(appliance, provider, provisioning):
    template_name = provisioning['template']
    vm_name = random_vm_name('k6tvm')
    prov_data = {'catalog': {'vm_name': vm_name}}
    vm = appliance.collections.infra_vms.instantiate(name=vm_name,
                                                     provider=provider,
                                                     template_name=template_name)
    note = ('template {} to vm {} on provider {}'.format(template_name, vm_name, provider.key))
    prov_data.update({
        'request': {
            'email': 'template_provisioner@example.com',
            'first_name': 'Template',
            'last_name': 'Provisioner',
            'notes': note}})
    view = navigate_to(vm.parent, 'Provision')
    view.form.fill_with(prov_data, on_change=view.form.submit_button)
    view.flash.assert_no_error()
    vm.wait_to_appear()
    yield vm
    vm.retire()


def test_k6t_provider_crud(provider):

    """
    Polarion:
        assignee: rhcf3_machine
        initialEstimate: 1/4h
        casecomponent: Infra
    """
    with update(provider):
        provider.name = fauxfactory.gen_alphanumeric(start="edited_")

    provider.delete()
    provider.wait_for_delete()


@pytest.mark.parametrize('custom_prov_data',
                         [{}, {'hardware': {'cpu_cores': '8', 'memory': '8192'}}],
                         ids=['via_lifecycle', 'override_template_values'])
def test_k6t_vm_crud(request, appliance, provider, provisioning, custom_prov_data):
    """
    Polarion:
        assignee: rhcf3_machine
        initialEstimate: 1/4h
        casecomponent: Infra
    """
    vm_name = random_vm_name('k6tvm')
    prov_data = {'catalog': {'vm_name': vm_name}}
    provider.refresh_provider_relationships()
    prov_data.update(custom_prov_data)
    template = provisioning['template']
    do_vm_provisioning(appliance, template, provider, vm_name, prov_data, request, wait=False)
    logger.info('Waiting for cfme provision request for vm %s', vm_name)
    request_description = 'Provision from [{}] to [{}]'.format(template, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui', num_sec=300)
    assert provision_request.is_succeeded(method='ui'), \
        ("Provisioning failed with the message {}".format(provision_request.row.last_message.text))


@pytest.mark.parametrize('from_details', ['True', 'False'], ids=['from_details', 'from_all_view'])
@pytest.mark.parametrize(['power_option', 'vm_state'],
                         [('Power On', 'currentstate-on'), ('Power Off', 'currentstate-off')],
                         ids=['PowerOn', 'PowerOff'])
def test_vm_power_management(request, appliance, provider, temp_vm,
                             from_details, power_option, vm_state):
    """
    Polarion:
        assignee: rhcf3_machine
        initialEstimate: 1/4h
        casecomponent: Infra
    """
    # TODO: use wrapanapi to check power state before applying it
    temp_vm.power_control_from_cfme(from_details=from_details, option=power_option)
    provider.refresh_provider_relationships()
    assert vm_state in temp_vm.find_quadicon().data['state']
