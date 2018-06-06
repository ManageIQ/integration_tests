# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.pxe import get_pxe_server_from_config, get_template_from_config
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils import testgen
from cfme.utils.conf import cfme_data
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    test_requirements.service,
    pytest.mark.tier(2)
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [InfraProvider], required_fields=[
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
    argnames = argnames
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
def catalog_item(appliance, provider, dialog, catalog, provisioning,
                 setup_pxe_servers_vm_prov):
    # generate_tests makes sure these have values
    pxe_template, host, datastore, pxe_server, pxe_image, pxe_kickstart, pxe_root_password,\
        pxe_image_type, pxe_vlan = map(
            provisioning.get, (
                'pxe_template', 'host', 'datastore', 'pxe_server', 'pxe_image', 'pxe_kickstart',
                'pxe_root_password', 'pxe_image_type', 'vlan'
            )
        )

    provisioning_data = {
        'catalog': {'catalog_name': {'name': pxe_template, 'provider': provider.name},
                    'provision_type': 'PXE',
                    'pxe_server': pxe_server,
                    'pxe_image': {'name': pxe_image},
                    'vm_name': random_vm_name('pxe_service')},
        'environment': {'datastore_name': {'name': datastore},
                        'host_name': {'name': host}},
        'customize': {'root_password': pxe_root_password,
                      'custom_template': {'name': pxe_kickstart}},
        'network': {'vlan': partial_match(pxe_vlan)},
    }

    item_name = fauxfactory.gen_alphanumeric()
    return appliance.collections.catalog_items.create(
        provider.catalog_item_type,
        name=item_name,
        description="my catalog", display_in=True, catalog=catalog,
        dialog=dialog, prov_data=provisioning_data)


@pytest.mark.rhv1
@pytest.mark.usefixtures('setup_pxe_servers_vm_prov')
def test_pxe_servicecatalog(appliance, setup_provider, provider, catalog_item, request):
    """Tests RHEV PXE service catalog

    Metadata:
        test_flag: pxe, provision
    """
    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            "{}_0001".format(vm_name), provider).delete_from_provider()
    )
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    # nav to requests page happens on successful provision
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request(num_sec=3600)
    msg = "Provisioning failed with the message {}".format(provision_request.rest.message)
    assert provision_request.is_succeeded(), msg
