# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.infrastructure.provider.kubevirt import KubeVirtProvider
from cfme.provisioning import do_vm_provisioning
from cfme.utils.generators import random_vm_name
from cfme.utils.update import update


pytestmark = [
    pytest.mark.provider([KubeVirtProvider], scope="module")
]


@pytest.fixture
def vm_name():
    vm_name = random_vm_name('provt')
    return vm_name


def test_cnv_prsovider_crud(provider):
    provider.create()

    with update(provider):
        provider.name = fauxfactory.gen_alphanumeric() + '_updated'

    provider.delete(cancel=False)
    provider.wait_for_delete()


def test_cnv_vm_crud(request, appliance, provider, setup_provider, vm_name):

    template = provisioning['template']

    provisioning_data = {
        'catalog': {
            'vm_name': vm_name
        }
    }

    do_vm_provisioning(appliance, template, provider, vm_name, provisioning_data, request)
