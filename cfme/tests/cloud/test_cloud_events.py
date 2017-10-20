# -*- coding: utf-8 -*-
"""This module tests only cloud specific events"""
import pytest
import yaml

from cfme.common.vm import VM
from cfme.cloud.provider.azure import AzureProvider
from cfme.utils.generators import random_vm_name


pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([AzureProvider], scope='module')
]


def test_manage_nsg_group(provider, setup_provider, register_event):
    """
    tests that create/remove azure network security groups events are received and parsed by CFME
    """

    nsg_name = random_vm_name(context='nsg')
    resource_group = provider.data['provisioning']['resource_group']

    # registering add/remove network security group events
    # we need to check raw data by regexps, since many azure events aren't parsed by CFME yet

    def add_cmp(_, y):
        data = yaml.load(y)
        return (data['resourceId'].endswith(nsg_name) and
                (data['status']['value'] == 'Accepted' and
                 data['subStatus']['value'] == 'Created') or
                data['status']['value'] == 'Succeeded')

    fd_add_attr = {'full_data': 'will be ignored',
                   'cmp_func': add_cmp}

    # add network security group event
    register_event(fd_add_attr, source=provider.type.upper(),
                   event_type='networkSecurityGroups_write_EndRequest')

    def rm_cmp(_, y):
        data = yaml.load(y)
        return data['resourceId'].endswith(nsg_name) and data['status']['value'] == 'Succeeded'

    fd_rm_attr = {'full_data': 'will be ignored',
                  'cmp_func': rm_cmp}

    # remove network security group
    register_event(fd_rm_attr, source=provider.type.upper(),
                   event_type='networkSecurityGroups_delete_EndRequest')

    # creating and removing network security group
    provider.mgmt.create_netsec_group(nsg_name, resource_group)
    provider.mgmt.remove_netsec_group(nsg_name, resource_group)


def test_vm_capture(request, provider, setup_provider, register_event):
    """
    tests that generalize and capture vm azure events are received and parsed by CFME
    """

    mgmt = provider.mgmt
    vm = VM.factory(random_vm_name(context='capture'), provider)

    if not mgmt.does_vm_exist(vm.name):
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
        vm.refresh_relationships()

    # # deferred delete vm
    request.addfinalizer(vm.delete_from_provider)

    def cmp_function(_, y):
        data = yaml.load(y)
        return data['resourceId'].endswith(vm.name) and data['status']['value'] == 'Succeeded'
    full_data_attr = {'full_data': 'will be ignored',
                      'cmp_func': cmp_function}

    # generalize event
    register_event(full_data_attr, source='AZURE',
                   event_type='virtualMachines_generalize_EndRequest')
    # capture event
    register_event(full_data_attr, source='AZURE', event_type='virtualMachines_capture_EndRequest')

    # capture vm
    image_name = vm.name
    resource_group = provider.data['provisioning']['resource_group']

    mgmt.capture_vm(vm.name, 'templates', image_name, resource_group=resource_group)

    # delete remaining image
    container = 'system'
    blob_images = mgmt.list_blob_images(container)
    # removing both json and vhd files
    test_image = [img for img in blob_images if image_name in img][-1]

    mgmt.remove_blob_image(test_image, container)
