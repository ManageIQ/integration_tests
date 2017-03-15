# -*- coding: utf-8 -*-
"""This module tests only cloud specific events"""
import pytest
import yaml

from cfme.common.vm import VM
from cfme.cloud.provider.azure import AzureProvider
from utils import testgen
from utils.appliance import get_or_create_current_appliance
from utils.events import EventBuilder
from utils.generators import random_vm_name


pytestmark = [
    pytest.mark.tier(3)
]
pytest_generate_tests = testgen.generate([AzureProvider], scope='module')


@pytest.mark.uncollectif(lambda provider: not provider.one_of(AzureProvider))
def test_manage_nsg_group(provider, setup_provider, register_event):
    """
    tests that create/remove azure network security groups events are received and parsed by CFME
    """

    nsg_name = random_vm_name(context='nsg')
    resource_group = provider.data['provisioning']['resource_group']

    # registering add/remove network security group events
    # we need to check raw data by regexps, since many azure events aren't parsed by CFME yet
    builder = EventBuilder(get_or_create_current_appliance())

    def add_cmp(_, y):
        data = yaml.load(y)
        return data['resourceId'].endswith(nsg_name) and data['status']['value'] == 'Accepted' and \
            data['subStatus']['value'] == 'Created'

    fd_add_attr = {'full_data': 'will be ignored',
                   'cmp_func': add_cmp}

    def rm_cmp(_, y):
        data = yaml.load(y)
        return data['resourceId'].endswith(nsg_name) and data['status']['value'] == 'Succeeded' \
            and len(data['subStatus']['value']) == 0

    fd_rm_attr = {'full_data': 'will be ignored',
                  'cmp_func': rm_cmp}

    add_event = builder.new_event(fd_add_attr, source=provider.type.upper(),
                                  event_type='networkSecurityGroups_write_EndRequest')
    register_event(add_event)

    remove_event = builder.new_event(fd_rm_attr, source=provider.type.upper(),
                                     event_type='networkSecurityGroups_delete_EndRequest')
    register_event(remove_event)

    # creating and removing network security group
    provider.mgmt.create_netsec_group(nsg_name, resource_group)
    provider.mgmt.remove_netsec_group(nsg_name, resource_group)


@pytest.mark.uncollectif(lambda provider: not provider.one_of(AzureProvider))
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

    # register event
    builder = EventBuilder(get_or_create_current_appliance())

    def cmp_function(_, y):
        data = yaml.load(y)
        return data['resourceId'].endswith(vm.name) and data['status']['value'] == 'Succeeded'
    full_data_attr = {'full_data': 'will be ignored',
                      'cmp_func': cmp_function}

    generalize_event = builder.new_event(full_data_attr, source='AZURE',
                                         event_type='virtualMachines_generalize_EndRequest')
    register_event(generalize_event)

    capture_event = builder.new_event(full_data_attr, source='AZURE',
                                      event_type='virtualMachines_capture_EndRequest')
    register_event(capture_event)

    # capture vm
    image_name = vm.name
    resource_group = provider.data['provisioning']['resource_group']

    mgmt.capture_vm(vm.name, resource_group, 'templates', image_name)

    # delete remaining image
    container = 'system'
    blob_images = mgmt.list_blob_images(container)
    # removing both json and vhd files
    test_image = [img for img in blob_images if image_name in img][-1]

    mgmt.remove_blob_image(test_image, container)
