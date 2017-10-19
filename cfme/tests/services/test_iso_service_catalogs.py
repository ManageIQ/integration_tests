# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.pxe import get_template_from_config, ISODatastore
from cfme import test_requirements
from cfme.utils import testgen
from cfme.utils.log import logger
from cfme.utils.conf import cfme_data
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('vm_name', 'uses_infra_providers'),
    test_requirements.service,
    pytest.mark.tier(2)
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [InfraProvider], required_fields=[
            'iso_datastore',
            ['provisioning', 'host'],
            ['provisioning', 'datastore'],
            ['provisioning', 'iso_template'],
            ['provisioning', 'iso_file'],
            ['provisioning', 'iso_kickstart'],
            ['provisioning', 'iso_root_password'],
            ['provisioning', 'iso_image_type'],
            ['provisioning', 'vlan'],
        ])
    argnames = argnames + ['iso_cust_template', 'iso_datastore']

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        iso_cust_template = args['provider'].data['provisioning']['iso_kickstart']
        if iso_cust_template not in cfme_data.get('customization_templates', {}).keys():
            continue

        argvalues[i].append(get_template_from_config(iso_cust_template))
        argvalues[i].append(ISODatastore(args['provider'].name))
        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="function")
def setup_iso_datastore(setup_provider_modscope, iso_cust_template, iso_datastore, provisioning):
    if not iso_datastore.exists():
        iso_datastore.create()
    iso_datastore.set_iso_image_type(provisioning['iso_file'], provisioning['iso_image_type'])
    if not iso_cust_template.exists():
        iso_cust_template.create()


@pytest.yield_fixture(scope="function")
def catalog_item(setup_provider, provider, vm_name, dialog, catalog, provisioning):
    iso_template, host, datastore, iso_file, iso_kickstart,\
        iso_root_password, iso_image_type, vlan = map(provisioning.get, ('pxe_template', 'host',
                                'datastore', 'iso_file', 'iso_kickstart',
                                'iso_root_password', 'iso_image_type', 'vlan'))

    provisioning_data = {
        'catalog': {'vm_name': vm_name,
                    'provision_type': 'ISO',
                    'iso_file': {'name': iso_file},
                    },
        'environment': {'host_name': {'name': host},
                        'datastore_name': {'name': datastore},
                        },
        'customize': {'custom_template': {'name': iso_kickstart},
                      'root_password': iso_root_password,
                      },
        'network': {'vlan': vlan,
                    },
    }

    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="RHEV", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=dialog, catalog_name=iso_template,
                  provider=provider, prov_data=provisioning_data)
    yield catalog_item


@pytest.mark.usefixtures('setup_iso_datastore')
@pytest.mark.meta(blockers=[BZ(1358069, forced_streams=["5.6", "5.7", "upstream"])])
def test_rhev_iso_servicecatalog(appliance, setup_provider, provider, catalog_item, request):
    """Tests RHEV ISO service catalog

    Metadata:
        test_flag: iso, provision
    """
    vm_name = catalog_item.provisioning_data['catalog']["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    catalog_item.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    # nav to requests page happens on successful provision
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    assert provision_request.is_succeeded()
