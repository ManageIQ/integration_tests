# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.provisioning import do_vm_provisioning
from cfme.infrastructure.pxe import get_template_from_config
from utils.conf import cfme_data
from utils import ssh
from utils import testgen
from utils.wait import wait_for

pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.meta(server_roles="+automate +notifier")
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'provisioning')
    argnames = argnames + ['cloud_init_template']

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # No provisioning data available
            continue

        if args['provider'].type == "scvmm" or args['provider'].type == 'virtualcenter':
            continue

        # required keys should be a subset of the dict keys set
        if not {'ci-template', 'ci-username', 'ci-pass', 'template'}.issubset(
                args['provisioning'].viewkeys()):
            continue

        cloud_init_template = args['provisioning']['ci-template']
        if cloud_init_template not in cfme_data.get('customization_templates', {}).keys():
            continue

        argvalues[i].append(get_template_from_config(cloud_init_template))

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def setup_ci_template(cloud_init_template):
    if not cloud_init_template.exists():
        cloud_init_template.create()


@pytest.fixture(scope="function")
def vm_name():
    vm_name = 'test_tmpl_prov_%s' % fauxfactory.gen_alphanumeric()
    return vm_name


def test_provision_cloud_init(setup_provider, provider, setup_ci_template, provisioning,
                              vm_name, smtp_test, request):
    """Tests cloud init provisioning

    Metadata:
        test_flag: cloud_init, provision
        suite: infra_provisioning
    """
    # generate_tests makes sure these have values
    template = provisioning.get('ci-image', None) or provisioning['image']['name']
    host, datastore = map(provisioning.get, ('host', 'datastore'))

    mgmt_system = provider.get_mgmt_system()

    request.addfinalizer(lambda: cleanup_vm(vm_name, provider))

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
        'provision_type': 'Native Clone',
        'custom_template': {'name': [provisioning['ci-template']]},
    }

    try:
        provisioning_data['vlan'] = provisioning['vlan']
    except KeyError:
        # provisioning['vlan'] is required for rhevm provisioning
        if provider.type == 'rhevm':
            raise pytest.fail('rhevm requires a vlan value in provisioning info')

    do_vm_provisioning(template, provider, vm_name, provisioning_data, request, smtp_test,
                       num_sec=900)

    connect_ip, tc = wait_for(mgmt_system.get_ip_address, [vm_name], num_sec=300,
                              handle_exception=True)

    # Check that we can at least get the uptime via ssh this should only be possible
    # if the username and password have been set via the cloud-init script so
    # is a valid check
    sshclient = ssh.SSHClient(hostname=connect_ip, username=provisioning['ci-username'],
                              password=provisioning['ci-pass'])
    wait_for(sshclient.uptime, num_sec=200, handle_exception=True)
