# -*- coding: utf-8 -*-
# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
import pytest

from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme.cloud.instance import Instance
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.infrastructure.pxe import get_template_from_config
from cfme.utils import ssh
from cfme.utils.generators import random_vm_name
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.provider([CloudProvider], required_fields=[
        ['provisioning', 'ci-template'],
        ['provisioning', 'ci-username'],
        ['provisioning', 'ci-pass'],
        ['provisioning', 'ci-image']],
        scope="module")
]


@pytest.fixture(scope="module")
def setup_ci_template(provider, appliance):
    cloud_init_template_name = provider.data['provisioning']['ci-template']
    get_template_from_config(
        cloud_init_template_name,
        create=True, appliance=appliance)


@pytest.fixture(scope="function")
def vm_name(request):
    vm_name = random_vm_name('ci')
    return vm_name


@pytest.mark.tier(3)
def test_provision_cloud_init(request, setup_provider, provider, provisioning,
                              setup_ci_template, vm_name):
    """ Tests provisioning from a template with cloud_init

    Metadata:
        test_flag: cloud_init, provision
    """
    image = provisioning.get('ci-image') or provisioning['image']['name']
    note = ('Testing cloud-init provisioning from image {} to vm {} on provider {}'.format(
        image, vm_name, provider.key))
    logger.info(note)

    mgmt_system = provider.mgmt

    instance = Instance.factory(vm_name, provider, image)

    request.addfinalizer(instance.cleanup_on_provider)
    inst_args = {
        'request': {'email': 'image_provisioner@example.com',
                    'first_name': 'Image',
                    'last_name': 'Provisioner',
                    'notes': note},
        'catalog': {
            'vm_name': vm_name},
        'customize': {
            'custom_template': {'name': provisioning['ci-template']}},
        'environment': {
            'availability_zone': provisioning.get('availability_zone', None),
            'security_groups': [provisioning.get('security_group', None)],
            'cloud_network': provisioning.get('cloud_network', None),
            'cloud_subnet': provisioning.get('cloud_subnet', None),
            'resource_groups': provisioning.get('resource_group', None)
        },
        'properties': {
            'instance_type': partial_match(provisioning.get('instance_type', None)),
            'guest_keypair': provisioning.get('guest_keypair', None)}
    }
    # GCE specific
    if provider.one_of(GCEProvider):
        recursive_update(inst_args, {
            'properties': {
                'boot_disk_size': provisioning['boot_disk_size'],
                'is_preemptible': True}
        })

    # Azure specific
    if provider.one_of(AzureProvider):
        # Azure uses different provisioning keys for some reason
        try:
            template = provider.data.templates.small_template
            vm_user = credentials[template.creds].username
            vm_password = credentials[template.creds].password
        except AttributeError:
            pytest.skip('Could not find small_template or credentials for {}'.format(provider.name))
        recursive_update(inst_args, {
            'environment': {
                'public_ip_address': 'New',
            },
            'customize': {
                'admin_username': vm_user,
                'root_password': vm_password}})

    if provider.one_of(OpenStackProvider):
        floating_ip = mgmt_system.get_first_floating_ip()
        inst_args['environment']['public_ip_address'] = floating_ip

    logger.info('Instance args: {}'.format(inst_args))

    instance.create(**inst_args)
    provision_request = provider.appliance.collections.requests.instantiate(vm_name,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    connect_ip = mgmt_system.get_ip_address(vm_name)

    # Check that we can at least get the uptime via ssh this should only be possible
    # if the username and password have been set via the cloud-init script so
    # is a valid check
    with ssh.SSHClient(hostname=connect_ip, username=provisioning['ci-username'],
                       password=provisioning['ci-pass']) as ssh_client:
        wait_for(ssh_client.uptime, num_sec=200, handle_exception=True)
