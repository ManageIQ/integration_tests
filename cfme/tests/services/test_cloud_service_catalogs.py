# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.cloud.provider import CloudProvider
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from cfme.web_ui import flash
from cfme import test_requirements
from utils import testgen
from utils.log import logger
from utils.wait import wait_for


pytestmark = [
    test_requirements.service,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.tier(2)
]


pytest_generate_tests = testgen.generate(
    [CloudProvider], required_fields=[['provisioning', 'image']], scope="module")


def test_cloud_catalog_item(setup_provider, provider, dialog, catalog, request, provisioning):
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
    provisioning_data = dict(
        vm_name=vm_name,
        instance_type=provisioning['instance_type'],
        security_groups=[provisioning['security_group']],
    )
    if provider.type == "azure":
        updates = dict(
            virtual_private_cloud=provisioning['virtual_private_cloud'],
            cloud_subnet=provisioning['cloud_subnet'],
            resource_group=[provisioning['resource_group']],
        )
    else:
        updates = dict(
            availability_zone=provisioning['availability_zone'],
            cloud_tenant=provisioning['cloud_tenant'],
            cloud_network=provisioning['cloud_network'],
            guest_keypair=provisioning['guest_keypair'],
            boot_disk_size=provisioning['boot_disk_size']
        )
    provisioning_data.update(updates)
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
    service_catalogs = ServiceCatalogs(catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s', item_name)
    row_description = item_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=1200, delay=20)
    assert row.request_state.text == 'Finished'
