"""This module tests only cloud specific events"""
import time

import pytest

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([AzureProvider], scope='module'),
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.events
]


def test_manage_nsg_group(appliance, provider, register_event):
    """
    tests that create/remove azure network security groups events are received and parsed by CFME

    Metadata:
        test_flag: events

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/8h
        casecomponent: Events
        caseimportance: medium
    """

    nsg_name = random_vm_name(context='nsg')
    resource_group = provider.data['provisioning']['resource_group']

    # registering add/remove network security group events
    # we need to check raw data by regexps, since many azure events aren't parsed by CFME yet

    def add_cmp(_, data):
        """ comparison function, data is expected to be a dictionary, containing the keys below """

        # In 5.10 data does not have 'status' or 'subStatus' key
        if appliance.version < '5.10':
            compare = (
                data['resourceId'].endswith(nsg_name) and
                (
                    data['status']['value'] == 'Accepted' and
                    data['subStatus']['value'] == 'Created'
                ) or
                data['status']['value'] == 'Succeeded'
            )
        else:
            compare = data['resourceId'].endswith(nsg_name)

        return compare

    fd_add_attr = {'full_data': 'will be ignored',
                   'cmp_func': add_cmp}

    # add network security group event
    register_event(fd_add_attr, source=provider.type.upper(),
                   event_type='networkSecurityGroups_write_EndRequest')

    def rm_cmp(_, data):
        """ comparison function, data is expected to be a dictionary, containing the keys below """

        if appliance.version < '5.10':
            compare = (data['resourceId'].endswith(nsg_name) and
                       data['status']['value'] == 'Succeeded')
        else:
            compare = data['resourceId'].endswith(nsg_name)

        return compare

    fd_rm_attr = {'full_data': 'will be ignored',
                  'cmp_func': rm_cmp}

    # remove network security group
    register_event(fd_rm_attr, source=provider.type.upper(),
                   event_type='networkSecurityGroups_delete_EndRequest')

    # creating and removing network security group
    provider.mgmt.create_netsec_group(nsg_name, resource_group)
    # wait for a minute before deleting the security group so CFME has time to receive the event
    time.sleep(60)
    provider.mgmt.remove_netsec_group(nsg_name, resource_group)


@pytest.mark.meta(blockers=[BZ(1724312), BZ(1733383)], automates=[1724312, 1733383])
def test_vm_capture(appliance, request, provider, register_event):
    """
    tests that generalize and capture vm azure events are received and parsed by CFME

    Metadata:
        test_flag: events, provision

    Bugzilla:
        1724312
        1733383

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/8h
        casecomponent: Events
        caseimportance: medium
    """

    vm = appliance.collections.cloud_instances.instantiate(
        random_vm_name(context='capture'), provider)

    if not vm.exists_on_provider:
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
        vm.refresh_relationships()

    # # deferred delete vm
    request.addfinalizer(vm.cleanup_on_provider)

    def cmp_function(_, data):
        """ comparison function, data is expected to be a dictionary containing the keys below """
        if appliance.version < '5.10':
            compare = (data['resourceId'].endswith(vm.name) and
                       data['status']['value'] == 'Succeeded')
        else:
            compare = data['resourceId'].endswith(vm.name)

        return compare

    full_data_attr = {'full_data': 'will be ignored',
                      'cmp_func': cmp_function}

    # generalize event
    register_event(full_data_attr, source='AZURE',
                   event_type='virtualMachines_generalize_EndRequest')
    # capture event
    register_event(full_data_attr, source='AZURE', event_type='virtualMachines_capture_EndRequest')

    # capture vm
    vm.mgmt.capture(container='templates', image_name=vm.name)

    # delete remaining image
    # removing both json and vhd files, find_templates returns blob objects
    blob_images = provider.mgmt.find_templates(container='system', name=vm.name, only_vhd=False)
    logger.info('Found blobs on system container: %s', blob_images)
    for blob in blob_images:
        logger.info('Deleting blob %s', blob)
        blob.cleanup()
