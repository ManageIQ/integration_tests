"""Test to validate conversion host UI."""
import tempfile

import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.v2v_fixtures import get_conversion_data
from cfme.fixtures.v2v_fixtures import get_data
from cfme.fixtures.v2v_fixtures import vddk_url
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils import conf

pytestmark = [
    test_requirements.v2v,
    pytest.mark.provider(
        classes=[RHEVMProvider, OpenStackProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_VERSION,
        fixture_name="source_provider",
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.usefixtures("v2v_provider_setup"),
]


def get_vmware_ssh_key(transformation_method, source_provider):
    """Get vmware ssh keys from yaml required only when transformation method is SSH"""
    vmware_ssh_key = None
    if transformation_method == "SSH":
        ssh_key_name = source_provider.data['private-keys']['vmware-ssh-key']['credentials']
        vmware_ssh_key = conf.credentials[ssh_key_name]['password']
    return vmware_ssh_key


def get_tls_key(provider):
    """Get TLS cert from yaml for OSP provider"""
    tls_key_name = provider.data['private-keys']['tls_cert']['credentials']
    tls_cert_key = conf.credentials[tls_key_name]['password']
    return tls_cert_key


def test_add_conversion_host_ui_crud(appliance, delete_conversion_hosts,
                                     source_provider, provider):
    """
        Test CRUD operations for conversion host from UI
        Polarion:
            assignee: sshveta
            caseimportance: medium
            caseposneg: positive
            testtype: functional
            startsin: 5.10
            casecomponent: V2V
            initialEstimate: 1/4h
        """
    # Get conversion host key from target provider required for migration
    transformation_method = "VDDK"
    temp_file = tempfile.NamedTemporaryFile('w')
    with open(temp_file.name, 'w') as f:
        f.write(get_conversion_data(provider)["private_key"])
    conv_host_key = temp_file.name

    if provider.one_of(RHEVMProvider):
        hosts = [h.name for h in provider.hosts.all()]
        default_value = 'Default'
        osp_cert_switch = None
        osp_ca_cert = None
    else:
        hosts = provider.data['conversion_instances']
        default_value = 'admin'
        osp_cert_switch = True
        osp_ca_cert = get_tls_key(provider)

    conv_host_collection = appliance.collections.v2v_conversion_hosts
    for host in hosts:
        conv_host = conv_host_collection.create(
            target_provider=provider,
            cluster=get_data(provider, "clusters", default_value),
            hostname=host,
            conv_host_key=conv_host_key,
            transformation_method=transformation_method,
            vddk_library_path=vddk_url('VDDK67'),
            vmware_ssh_key=get_vmware_ssh_key(transformation_method, source_provider),
            osp_cert_switch=osp_cert_switch,
            osp_ca_cert=osp_ca_cert
        )
        assert conv_host.is_host_configured
        assert conv_host.remove_conversion_host()
        assert conv_host.is_host_removed
