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


def configure_conversion_host_ui(appliance, target_provider, hostname, default_value,
                                 conv_host_key, transformation_method,
                                 vmware_ssh_key, osp_cert_switch=None, osp_ca_cert=None):
    """ Configures conversion host from UI"""
    conv_host_collection = appliance.collections.v2v_conversion_hosts
    conv_host = conv_host_collection.create(
        target_provider=target_provider,
        cluster=get_data(target_provider, "clusters", default_value),
        hostname=hostname,
        conv_host_key=conv_host_key,
        transformation_method=transformation_method,
        vddk_library_path=vddk_url(),
        vmware_ssh_key=vmware_ssh_key,
        osp_cert_switch=osp_cert_switch,
        osp_ca_cert=osp_ca_cert
    )
    return conv_host


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
        rhev_hosts = [h.name for h in provider.hosts.all()]
        for host in rhev_hosts:
            conv_host = configure_conversion_host_ui(appliance, provider,
                                                     host, "Default",
                                                     conv_host_key, transformation_method,
                                                     get_vmware_ssh_key(transformation_method,
                                                                        source_provider))
            assert conv_host.is_host_configured
            assert conv_host.remove_conversion_host()

    else:
        conversion_instances = provider.data['conversion_instances']
        for instance in conversion_instances:
            conv_host = configure_conversion_host_ui(appliance, provider, instance, "admin",
                                                     conv_host_key, transformation_method,
                                                     get_vmware_ssh_key(transformation_method,
                                                                        source_provider),
                                                     osp_cert_switch=True,
                                                     osp_ca_cert=get_tls_key(provider))
            assert conv_host.is_host_configured
            assert conv_host.remove_conversion_host()
