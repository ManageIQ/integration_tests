# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.cloud.provider import CloudProvider
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.service_catalogs import ServiceCatalogs
from cfme import test_requirements
from cfme.utils import testgen
from cfme.utils.log import logger


pytestmark = [
    test_requirements.service,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.tier(2)
]


pytest_generate_tests = testgen.generate(
    [CloudProvider], required_fields=[['provisioning', 'image']], scope="module")


def test_cloud_catalog_item(appliance, setup_provider, provider, dialog, catalog, request,
                            provisioning):
    """Tests cloud catalog item

    Metadata:
        test_flag: provision
    """
    vm_name = 'test{}'.format(fauxfactory.gen_alphanumeric())
    # GCE accepts only lowercase letters in VM name
    vm_name = vm_name.lower()
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    image = provisioning['image']['name']
    item_name = fauxfactory.gen_alphanumeric()
    provisioning_data = {
        'catalog': {'vm_name': vm_name,
                    },
        'properties': {'instance_type': provisioning['instance_type'],
                       },
        'environment': {'security_groups': [provisioning['security_group']],
                        },
    }

    if provider.type == "azure":
        env_updates = dict(
            cloud_network=provisioning['virtual_private_cloud'],
            cloud_subnet=provisioning['cloud_subnet'],
            resource_groups=[provisioning['resource_group']],
        )
    else:
        provisioning_data['properties']['guest_keypair'] = provisioning['guest_keypair']
        provisioning_data['properties']['boot_disk_size'] = provisioning['boot_disk_size']
        env_updates = dict(
            availability_zone=provisioning['availability_zone'],
            cloud_tenant=provisioning['cloud_tenant'],
            cloud_network=provisioning['cloud_network'])

    provisioning_data['environment'].update(env_updates)
    catalog_item = CatalogItem(item_type=provisioning['item_type'],
                               name=item_name,
                               description="my catalog",
                               display_in=True,
                               catalog=catalog,
                               dialog=dialog,
                               catalog_name=image,
                               provider=provider,
                               prov_data=provisioning_data)
    catalog_item.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', item_name)
    request_description = item_name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    assert provision_request.is_succeeded()
