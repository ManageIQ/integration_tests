# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.pxe import get_pxe_server_from_config
from cfme.infrastructure.pxe import get_template_from_config
from cfme.provisioning import do_vm_provisioning
from cfme.utils import testgen
from cfme.utils.conf import cfme_data

pytestmark = [
    pytest.mark.meta(server_roles="+automate +notifier"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.tier(2)
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [InfraProvider],
        required_fields=[
            ['provisioning', 'pxe_server'],
            ['provisioning', 'pxe_image'],
            ['provisioning', 'pxe_image_type'],
            ['provisioning', 'pxe_kickstart'],
            ['provisioning', 'pxe_template'],
            ['provisioning', 'datastore'],
            ['provisioning', 'host'],
            ['provisioning', 'pxe_root_password'],
            ['provisioning', 'vlan']
        ]
    )
    pargnames, pargvalues, pidlist = testgen.pxe_servers(metafunc)
    argnames = argnames
    pxe_server_names = [pval[0] for pval in pargvalues]

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(list(zip(argnames, argvalue_tuple)))

        provider = args['provider']

        if provider.one_of(SCVMMProvider):
            continue

        provisioning_data = provider.data['provisioning']

        pxe_server_name = provisioning_data['pxe_server']
        if pxe_server_name not in pxe_server_names:
            continue

        pxe_cust_template = provisioning_data['pxe_kickstart']
        if pxe_cust_template not in list(cfme_data.get('customization_templates', {}).keys()):
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope='module')
def pxe_server(appliance, provider):
    provisioning_data = provider.data['provisioning']
    pxe_server_name = provisioning_data['pxe_server']
    return get_pxe_server_from_config(pxe_server_name, appliance=appliance)


@pytest.fixture(scope='module')
def pxe_cust_template(appliance, provider):
    provisioning_data = provider.data['provisioning']
    pxe_cust_template = provisioning_data['pxe_kickstart']
    return get_template_from_config(pxe_cust_template, create=True, appliance=appliance)


@pytest.fixture(scope="function")
def setup_pxe_servers_vm_prov(pxe_server, pxe_cust_template, provisioning):
    if not pxe_server.exists():
        pxe_server.create()

    pxe_server.set_pxe_image_type(provisioning['pxe_image'], provisioning['pxe_image_type'])


@pytest.fixture(scope="function")
def vm_name():
    vm_name = 'test_pxe_prov_{}'.format(fauxfactory.gen_alphanumeric())
    return vm_name


@pytest.mark.rhv1
def test_pxe_provision_from_template(appliance, provider, vm_name, setup_provider,
                                     request, setup_pxe_servers_vm_prov):
    """Tests provisioning via PXE

    Metadata:
        test_flag: pxe, provision
        suite: infra_provisioning

    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        initialEstimate: 1/6h
        testtype: functional
        upstream: yes
    """

    # generate_tests makes sure these have values
    (
        pxe_template, host, datastore,
        pxe_server, pxe_image, pxe_kickstart,
        pxe_root_password, pxe_image_type, pxe_vlan
    ) = list(map(
        provider.data['provisioning'].get,
        (
            'pxe_template', 'host', 'datastore',
            'pxe_server', 'pxe_image', 'pxe_kickstart',
            'pxe_root_password', 'pxe_image_type', 'vlan'
        )
    ))

    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(vm_name, provider)
        .cleanup_on_provider())

    provisioning_data = {
        'catalog': {
            'vm_name': vm_name,
            'provision_type': 'PXE',
            'pxe_server': pxe_server,
            'pxe_image': {'name': pxe_image}},
        'environment': {
            'host_name': {'name': host},
            'datastore_name': {'name': datastore}},
        'customize': {
            'custom_template': {'name': pxe_kickstart},
            'root_password': pxe_root_password},
        'network': {
            'vlan': partial_match(pxe_vlan)}}

    do_vm_provisioning(appliance, pxe_template, provider, vm_name, provisioning_data, request,
                       num_sec=3600)
