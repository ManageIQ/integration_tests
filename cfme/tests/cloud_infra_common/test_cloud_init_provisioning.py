from contextlib import closing

import pytest
from widgetastic.utils import partial_match

import cfme.common.vm
from cfme import test_requirements
from cfme.base.credential import SSHCredential
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.pxe import get_template_from_config
from cfme.markers.env_markers.provider import providers
from cfme.tests.infrastructure.test_provisioning_dialog import check_all_tabs
from cfme.utils import ssh
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.ssh import connect_ssh
from cfme.utils.wait import wait_for


pf1 = ProviderFilter(classes=[CloudProvider, InfraProvider], required_fields=[['provisioning',
                                                                               'ci-template']])
pf2 = ProviderFilter(classes=[SCVMMProvider], inverted=True)  # SCVMM doesn't support cloud-init
pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.provider(gen_func=providers, filters=[pf1, pf2], scope="module")
]


def find_global_ipv6(vm):
    """
    Find global IPv6 on a VM if present.

    Args:
        vm: InfraVm object

    Returns: IPv6 as a string if found, False otherwise
    """
    all_ips = vm.mgmt.all_ips
    for ip in all_ips:
        if ':' in ip and not ip.startswith('fe80'):
            return ip
    return False


@pytest.fixture(scope="module")
def setup_ci_template(provider, appliance):
    cloud_init_template_name = provider.data['provisioning']['ci-template']
    get_template_from_config(
        cloud_init_template_name,
        create=True, appliance=appliance)


@pytest.fixture()
def vm_name():
    return random_vm_name('ci')


@pytest.mark.tier(3)
@test_requirements.provision
@pytest.mark.meta(automates=[BZ(1797706)])
def test_provision_cloud_init(appliance, request, setup_provider, provider, provisioning,
                        setup_ci_template, vm_name):
    """ Tests provisioning from a template with cloud_init

    Metadata:
        test_flag: cloud_init, provision

    Bugzilla:
        1619744
        1797706

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Provisioning
    """
    image = provisioning.get('ci-image') or provisioning['image']['name']
    note = ('Testing provisioning from image {} to vm {} on provider {}'.format(
        image, vm_name, provider.key))
    logger.info(note)

    mgmt_system = provider.mgmt

    inst_args = {
        'request': {'notes': note},
        'customize': {'custom_template': {'name': provisioning['ci-template']}},
        'template_name': image  # for image selection in before_fill
    }

    # TODO Perhaps merge this with stuff in test_provisioning_dialog.prov_data
    if provider.one_of(AzureProvider):
        inst_args['environment'] = {'public_ip_address': "New"}
    if provider.one_of(OpenStackProvider):
        ip_pool = provider.data['public_network']
        floating_ip = mgmt_system.get_first_floating_ip(pool=ip_pool)
        provider.refresh_provider_relationships()
        inst_args['environment'] = {'public_ip_address': floating_ip}
        inst_arg_props = inst_args.setdefault('properties', {})
        inst_arg_props['instance_type'] = partial_match(provisioning['ci-flavor-name'])

    if provider.one_of(InfraProvider) and appliance.version > '5.9':
        inst_args['customize']['customize_type'] = 'Specification'

    logger.info(f'Instance args: {inst_args}')

    collection = appliance.provider_based_collection(provider)
    instance = collection.create(vm_name, provider, form_values=inst_args)

    request.addfinalizer(instance.cleanup_on_provider)
    provision_request = provider.appliance.collections.requests.instantiate(vm_name,
                                                                   partial_check=True)
    check_all_tabs(provision_request, provider)
    provision_request.wait_for_request()
    wait_for(lambda: instance.ip_address is not None, num_sec=600)
    connect_ip = instance.ip_address
    assert connect_ip, "VM has no IP"

    # Check that we can at least get the uptime via ssh this should only be possible
    # if the username and password have been set via the cloud-init script so
    # is a valid check
    with ssh.SSHClient(hostname=connect_ip, username=provisioning['ci-username'],
                       password=provisioning['ci-pass']) as ssh_client:
        wait_for(ssh_client.uptime, num_sec=200, handle_exception=True)


@test_requirements.provision
@pytest.mark.provider([RHEVMProvider])
@pytest.mark.meta(automates=[1797706])
def test_provision_cloud_init_payload(appliance, request, setup_provider, provider, provisioning,
                                      vm_name):
    """
    Tests that options specified in VM provisioning dialog in UI are properly passed as a cloud-init
    payload to the newly provisioned VM.

    Metadata:
        test_flag: cloud_init, provision

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Provisioning
    """
    image = provisioning.get('ci-image', None)
    if not image:
        pytest.skip('No ci-image found in provider specification.')
    note = ('Testing provisioning from image {image} to vm {vm} on provider {provider}'.format(
        image=image, vm=vm_name, provider=provider.key))
    logger.info(note)

    ci_payload = {
        'root_password': 'mysecret',
        'address_mode': 'DHCP',
        'hostname': 'cimachine',
        'custom_template': {'name': 'oVirt cloud-init'}
    }

    THERE_IS_A_WAY_TO_CHECK_STATIC_IP_VM = False
    # TODO on review: How? Perhaps we can check the logs from the cloud-init somehow?

    if THERE_IS_A_WAY_TO_CHECK_STATIC_IP_VM:
        ci_payload.update({
            'address_mode': 'Static',
            'ip_address': '169.254.0.1',
            'subnet_mask': '29',
            'gateway': '169.254.0.2',
            'dns_servers': '169.254.0.3',
            'dns_suffixes': 'virt.lab.example.com',
        })

    inst_args = {
        'request': {'notes': note},
        'customize': {'customize_type': 'Specification'},
        'template_name': image
    }

    inst_args['customize'].update(ci_payload)
    logger.info(f'Instance args: {inst_args}')

    # Provision VM
    collection = appliance.provider_based_collection(provider)
    instance: cfme.common.vm.VM = collection.create(vm_name, provider, form_values=inst_args)
    request.addfinalizer(lambda: instance.cleanup_on_provider(handle_cleanup_exception=False))

    provision_request = provider.appliance.collections.requests.instantiate(vm_name,
                                                                            partial_check=True)
    check_all_tabs(provision_request, provider)
    provision_request.wait_for_request()

    creds = SSHCredential(principal="root", secret=ci_payload['root_password'])
    with closing(connect_ssh(instance.mgmt, creds, num_sec=60)) as ssh_client:
        # Check that correct hostname has been set
        hostname_cmd = ssh_client.run_command('hostname')
        assert hostname_cmd.success
        assert hostname_cmd.output.strip() == ci_payload['hostname']

        # Obtain network configuration script for eth0 and store it in a list
        network_cfg_cmd = ssh_client.run_command('cat /etc/sysconfig/network-scripts/ifcfg-eth0')
        assert network_cfg_cmd.success
        config_list = network_cfg_cmd.output.split('\n')

        # Compare contents of network script with cloud-init payload
        address_mode = ci_payload["address_mode"].lower()
        assert f'BOOTPROTO={"none" if address_mode == "static" else address_mode}' in config_list

        if THERE_IS_A_WAY_TO_CHECK_STATIC_IP_VM:
            assert 'IPADDR={}'.format(ci_payload['ip_address']) in config_list
            assert 'PREFIX={}'.format(ci_payload['subnet_mask']) in config_list
            assert 'GATEWAY={}'.format(ci_payload['gateway']) in config_list
            assert 'DNS1={}'.format(ci_payload['dns_servers']) in config_list
            assert 'DOMAIN={}'.format(ci_payload['dns_suffixes']) in config_list
