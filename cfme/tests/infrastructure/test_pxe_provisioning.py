# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from utils.conf import cfme_data
from cfme.common.provider import cleanup_vm
from cfme.infrastructure.pxe import get_pxe_server_from_config, get_template_from_config
from cfme.provisioning import do_vm_provisioning
from utils import testgen

pytestmark = [
    pytest.mark.meta(server_roles="+automate +notifier"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.tier(2)
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, required_fields=[
        ['provisioning', 'pxe_server'],
        ['provisioning', 'pxe_image'],
        ['provisioning', 'pxe_image_type'],
        ['provisioning', 'pxe_kickstart'],
        ['provisioning', 'pxe_template'],
        ['provisioning', 'datastore'],
        ['provisioning', 'host'],
        ['provisioning', 'pxe_root_password'],
        ['provisioning', 'vlan']
    ])
    pargnames, pargvalues, pidlist = testgen.pxe_servers(metafunc)
    argnames = argnames + ['pxe_server', 'pxe_cust_template']
    pxe_server_names = [pval[0] for pval in pargvalues]

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        if args['provider'].type == "scvmm":
            continue

        pxe_server_name = args['provider'].data['provisioning']['pxe_server']
        if pxe_server_name not in pxe_server_names:
            continue

        pxe_cust_template = args['provider'].data['provisioning']['pxe_kickstart']
        if pxe_cust_template not in cfme_data.get('customization_templates', {}).keys():
            continue

        argvalues[i].append(get_pxe_server_from_config(pxe_server_name))
        argvalues[i].append(get_template_from_config(pxe_cust_template))
        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="function")
def setup_pxe_servers_vm_prov(pxe_server, pxe_cust_template, provisioning):
    if not pxe_server.exists():
        pxe_server.create()
    pxe_server.set_pxe_image_type(provisioning['pxe_image'], provisioning['pxe_image_type'])
    if not pxe_cust_template.exists():
        pxe_cust_template.create()


@pytest.fixture(scope="function")
def vm_name():
    vm_name = 'test_pxe_prov_{}'.format(fauxfactory.gen_alphanumeric())
    return vm_name


@pytest.mark.usefixtures('setup_pxe_servers_vm_prov')
def test_pxe_provision_from_template(provider, vm_name, smtp_test, setup_provider,
                                     request, setup_pxe_servers_vm_prov):
    """Tests provisioning via PXE

    Metadata:
        test_flag: pxe, provision
        suite: infra_provisioning
    """

    # generate_tests makes sure these have values
    pxe_template, host, datastore, pxe_server, pxe_image, pxe_kickstart,\
        pxe_root_password, pxe_image_type, pxe_vlan = map(provider.data['provisioning'].get,
            ('pxe_template', 'host', 'datastore', 'pxe_server', 'pxe_image', 'pxe_kickstart',
             'pxe_root_password', 'pxe_image_type', 'vlan'))

    request.addfinalizer(lambda: cleanup_vm(vm_name, provider))

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
        'provision_type': 'PXE',
        'pxe_server': pxe_server,
        'pxe_image': {'name': [pxe_image]},
        'custom_template': {'name': [pxe_kickstart]},
        'root_password': pxe_root_password,
        'vlan': pxe_vlan,
    }

    do_vm_provisioning(pxe_template, provider, vm_name, provisioning_data, request, smtp_test,
                       num_sec=2100)
