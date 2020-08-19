from abc import ABCMeta
from abc import abstractmethod
from contextlib import closing
from contextlib import contextmanager
from typing import ContextManager
from typing import List

import pytest
import wrapanapi.entities
from widgetastic.utils import partial_match

import cfme.common.vm
from cfme import test_requirements
from cfme.base.credential import Credential
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
from cfme.utils.net import retry_connect
from cfme.utils.providers import ProviderFilter
from cfme.utils.ssh import connect_ssh
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import wait_for

REQUIRED_FIELDS = [['provisioning', 'ci-template']]

pf1 = ProviderFilter(classes=[CloudProvider, InfraProvider], required_fields=REQUIRED_FIELDS)
pf2 = ProviderFilter(classes=[SCVMMProvider], inverted=True)  # SCVMM doesn't support cloud-init
pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.provider(gen_func=providers, filters=[pf1, pf2], scope="module")
]


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


class AddressModeBase(metaclass=ABCMeta):
    def __repr__(self):
        return self.__class__.__name__

    @property
    @abstractmethod
    def bootproto(self) -> str:
        pass

    @abstractmethod
    @contextmanager
    def connect(self, provider: RHEVMProvider, instance: wrapanapi.entities.vm.Vm) \
            -> ContextManager[SSHClient]:
        pass

    def checks(self, ssh_client: SSHClient, config_list: List[str] = None):
        if config_list is None:
            config_list = self.get_config_list(ssh_client)

        # Compare contents of network script with cloud-init payload
        assert f'BOOTPROTO={self.bootproto}' in config_list

        # Check that correct hostname has been set
        hostname_cmd = ssh_client.run_command('hostname')
        assert hostname_cmd.success
        assert hostname_cmd.output.strip() == self.payload['hostname']

    @staticmethod
    def get_config_list(ssh_client: SSHClient):
        # Obtain network configuration script for eth0 and store it in a list
        network_cfg_cmd = ssh_client.run_command('cat /etc/sysconfig/network-scripts/ifcfg-eth0')
        assert network_cfg_cmd.success
        config_list = network_cfg_cmd.output.split('\n')
        return config_list

    @property
    @abstractmethod
    def payload(self):
        return {
            'root_password': 'mysecret',
            'hostname': 'cimachine',
            'custom_template': {'name': 'oVirt cloud-init'}
        }


class DHCPAddressMode(AddressModeBase):
    bootproto = "dhcp"

    @property
    def payload(self):
        return dict(super().payload, address_mode='DHCP')

    @contextmanager
    def connect(self, provider, instance):
        vm_creds = Credential('root', self.payload['root_password'])
        with connect_ssh(instance, creds=vm_creds, num_sec=300) as ssh_client:
            yield ssh_client


class StaticAddressMode(AddressModeBase):
    bootproto = "none"

    @property
    def payload(self):
        return dict(super().payload,
                    address_mode='Static',
                    ip_address='169.254.0.1',
                    subnet_mask='29',
                    gateway='169.254.0.2',
                    dns_servers='169.254.0.3',
                    dns_suffixes='virt.lab.example.com')

    def checks(self, ssh_client, config_list=None):
        static_mode_payload = self.payload
        if config_list is None:
            config_list = self.get_config_list(ssh_client)

        assert 'IPADDR={}'.format(static_mode_payload['ip_address']) in config_list
        assert 'PREFIX={}'.format(static_mode_payload['subnet_mask']) in config_list
        assert 'GATEWAY={}'.format(static_mode_payload['gateway']) in config_list
        assert 'DNS1={}'.format(static_mode_payload['dns_servers']) in config_list
        assert 'DOMAIN={}'.format(static_mode_payload['dns_suffixes']) in config_list

    @contextmanager
    def connect(self, provider, instance):
        static_mode_payload = self.payload
        wait_for(lambda: static_mode_payload['ip_address'] in instance.all_ips, timeout='5m')

        # Any host that works can be used. To keep things simple, just pick the first one with
        # fingers crossed.
        jump_host_config = provider.data['hosts'][0]

        jump_host_creds = Credential.from_config(jump_host_config['credentials']['default'])
        jump_host_session = SSHClient(hostname=jump_host_config['name'],
                                      username=jump_host_creds.principal,
                                      password=jump_host_creds.secret)

        def _connection_factory(ip):
            return jump_host_session.tunnel_to(
                hostname=ip,
                username='root', password=static_mode_payload['root_password'],
                timeout=ssh.CONNECT_TIMEOUT)

        # Cleanup this explicitly because we can get to problems with ordering the cleanups of
        # tunneled connections and the tunnels at the session end.
        # Note that the SSHClient.__exit__ does NOT close the connection.
        with closing(retry_connect(
                lambda: instance.all_ips,
                _connection_factory,
                num_sec=ssh.CONNECT_RETRIES_TIMEOUT, delay=ssh.CONNECT_SSH_DELAY)) as ssh_client:
            yield ssh_client


@test_requirements.provision
@pytest.mark.provider([RHEVMProvider], required_fields=REQUIRED_FIELDS)
@pytest.mark.meta(automates=[1797706])
@pytest.mark.parametrize("address_mode", [StaticAddressMode(), DHCPAddressMode()], ids=repr)
def test_provision_cloud_init_payload(appliance, request, setup_provider, provider: RHEVMProvider,
                                      provisioning, vm_name, address_mode):
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

    inst_args = {
        'request': {'notes': note},
        'customize': {'customize_type': 'Specification'},
        'template_name': image
    }

    inst_args['customize'].update(address_mode.payload)
    logger.info(f'Instance args: {inst_args}')

    # Provision VM
    collection = appliance.provider_based_collection(provider)
    instance: cfme.common.vm.VM = collection.create(vm_name, provider, form_values=inst_args)
    request.addfinalizer(lambda: instance.cleanup_on_provider(handle_cleanup_exception=False))

    provision_request = provider.appliance.collections.requests.instantiate(vm_name,
                                                                            partial_check=True)
    check_all_tabs(provision_request, provider)
    provision_request.wait_for_request()

    with address_mode.connect(provider, instance.mgmt) as ssh_client:
        address_mode.checks(ssh_client)
