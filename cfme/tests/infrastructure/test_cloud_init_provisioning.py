# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.vm import VM
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.provisioning import do_vm_provisioning
from cfme.infrastructure.pxe import get_template_from_config
from cfme.utils import ssh
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.meta(server_roles="+automate +notifier"),
    pytest.mark.provider([RHEVMProvider],
                         required_fields=[['provisioning', 'ci-template'],
                                          ['provisioning', 'ci-username'],
                                          ['provisioning', 'ci-pass'],
                                          ['provisioning', 'image'],
                                          ['provisioning', 'vlan']],
                         scope='module'),
]


@pytest.fixture(scope="module")
def setup_ci_template(provisioning, appliance):
    cloud_init_template_name = provisioning['ci-template']
    get_template_from_config(cloud_init_template_name, create=True, appliance=appliance)


@pytest.fixture(scope="function")
def vm_name():
    vm_name = 'test_tmpl_prov_{}'.format(fauxfactory.gen_alphanumeric())
    return vm_name


def test_provision_cloud_init(appliance, setup_provider, provider, setup_ci_template,
                              vm_name, smtp_test, request, provisioning):
    """Tests cloud init provisioning

    Metadata:
        test_flag: cloud_init, provision
        suite: infra_provisioning
    """
    # generate_tests makes sure these have values
    template = provisioning.get('ci-image') or provisioning['image']['name']
    host, datastore, vlan = map(provisioning.get, ('host', 'datastore', 'vlan'))

    request.addfinalizer(lambda: VM.factory(vm_name, provider).cleanup_on_provider())

    provisioning_data = {
        'catalog': {
            'provision_type': 'Native Clone',
            'vm_name': vm_name},
        'environment': {
            'host_name': {'name': host},
            'datastore_name': {'name': datastore}},
        'network': {
            'vlan': vlan},
        'customize': {
            'custom_template': {'name': [provisioning['ci-template']]}}
    }

    do_vm_provisioning(appliance, template, provider, vm_name, provisioning_data, request,
                       smtp_test, num_sec=900)

    connect_ip, tc = wait_for(provider.mgmt.get_ip_address, [vm_name], num_sec=300,
                              handle_exception=True)

    # Check that we can at least get the uptime via ssh this should only be possible
    # if the username and password have been set via the cloud-init script so
    # is a valid check
    with ssh.SSHClient(hostname=connect_ip, username=provisioning['ci-username'],
                       password=provisioning['ci-pass']) as ssh_client:
        wait_for(ssh_client.uptime, num_sec=200, handle_exception=True)
