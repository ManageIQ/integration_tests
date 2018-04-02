# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.vm import VM
from cfme.infrastructure.provider.kubevirt import KubeVirtProvider
from cfme.provisioning import do_vm_provisioning
from cfme.utils.generators import random_vm_name
from cfme.utils.update import update


pytestmark = [
    pytest.mark.provider([KubeVirtProvider], scope="module")
]


@pytest.fixture
def vm_name():
    vm_name = random_vm_name('k6tvm')
    return vm_name


@pytest.fixture
def test_vm(provider, vm_name):
    vm = VM.factory(vm_name, provider)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm.refresh_relationships()
    yield vm
    vm.cleanup_on_provider()


def test_k6t_provider_crud(provider):
    provider.create()

    with update(provider):
        provider.name = fauxfactory.gen_alphanumeric() + '_updated'

    provider.delete(cancel=False)
    provider.wait_for_delete()


@pytest.mark.parametrize('custom_prov_data',
                         [{}, {'hardware': {'cpu_cores': '8', 'memory': '8192'}}],
                         ids=['via_lifecycle', 'override_template_values']
                         )
def test_k6t_vm_crud(request, appliance, provider, vm_name, provisioning,
                     custom_prov_data):
    provider.create()
    # TODO: replace with setup_provider fixture
    template = provisioning['template']

    provisioning_data = {
        'catalog': {
            'vm_name': vm_name
        }
    }
    provisioning_data.update(custom_prov_data)

    do_vm_provisioning(appliance, template, provider, vm_name, provisioning_data, request)


def test_vm_power_management(request, appliance, provider, test_vm):
    pass
