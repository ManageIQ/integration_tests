import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.pxe import get_template_from_config
from cfme.infrastructure.pxe import ISODatastore
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.version import Version


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    test_requirements.service,
    pytest.mark.tier(2),
    pytest.mark.provider([InfraProvider], required_fields=[
        'iso_datastore',
        ['provisioning', 'host'],
        ['provisioning', 'datastore'],
        ['provisioning', 'iso_template'],
        ['provisioning', 'iso_file'],
        ['provisioning', 'iso_kickstart'],
        ['provisioning', 'iso_root_password'],
        ['provisioning', 'iso_image_type'],
        ['provisioning', 'vlan'],
    ], scope="module")
]


@pytest.fixture(scope="module")
def iso_cust_template(provider, appliance):
    iso_cust_template = provider.data['provisioning']['iso_kickstart']
    try:
        return get_template_from_config(iso_cust_template, create=True, appliance=appliance)
    except KeyError:
        pytest.skip("No such template '{}' available in 'customization_templates'".format(
            iso_cust_template
        ))


@pytest.fixture(scope="module")
def iso_datastore(provider, appliance):
    return ISODatastore(provider.name, appliance=appliance)


@pytest.fixture(scope="function")
def setup_iso_datastore(setup_provider, iso_cust_template, iso_datastore, provisioning):
    if not iso_datastore.exists():
        iso_datastore.create()
    iso_datastore.set_iso_image_type(provisioning['iso_file'], provisioning['iso_image_type'])


@pytest.fixture(scope="function")
def catalog_item(appliance, provider, dialog, catalog, provisioning):
    (iso_template,
     host,
     datastore,
     iso_file,
     iso_kickstart,
     iso_root_password,
     iso_image_type,
     vlan) = tuple(map(provisioning.get,
                     ('pxe_template',
                      'host',
                      'datastore',
                      'iso_file',
                      'iso_kickstart',
                      'iso_root_password',
                      'iso_image_type',
                      'vlan')))

    provisioning_data = {
        'catalog': {'catalog_name': {'name': iso_template, 'provider': provider.name},
                    'vm_name': random_vm_name('iso_service'),
                    'provision_type': 'ISO',
                    'iso_file': {'name': iso_file}},
        'environment': {'host_name': {'name': host},
                        'datastore_name': {'name': datastore}},
        'customize': {'custom_template': {'name': iso_kickstart},
                      'root_password': iso_root_password},
        'network': {'vlan': partial_match(vlan)},
    }

    item_name = fauxfactory.gen_alphanumeric(15, start="cat_item_")
    return appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.RHV,
        name=item_name,
        description="my catalog", display_in=True, catalog=catalog,
        dialog=dialog,
        prov_data=provisioning_data
    )


@test_requirements.rhev
@pytest.mark.meta(blockers=[BZ(1783355, forced_streams=["5.11", "5.10"],
                               unblock=lambda provider: provider.version != Version("4.4"))])
def test_rhev_iso_servicecatalog(appliance, provider, setup_provider, setup_iso_datastore,
                                 catalog_item, request):
    """Tests RHEV ISO service catalog

    Metadata:
        test_flag: iso, provision

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Services
    """
    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            f"{vm_name}0001", provider).cleanup_on_provider()
    )
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    # nav to requests page happens on successful provision
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = f"Provisioning failed with the message {provision_request.rest.message}"
    assert provision_request.is_succeeded(), msg
