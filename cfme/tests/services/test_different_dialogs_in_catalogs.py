# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.service_dialogs import DialogCollection
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.infrastructure.provider import InfraProvider
from cfme.common.provider import cleanup_vm
from cfme.utils import testgen
from cfme.utils.log import logger
from cfme.utils.blockers import BZ


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.usefixtures('vm_name', 'catalog_item', 'uses_infra_providers'),
    test_requirements.service,
    pytest.mark.long_running
]


pytest_generate_tests = testgen.generate([InfraProvider], required_fields=[
    ['provisioning', 'template'],
    ['provisioning', 'host'],
    ['provisioning', 'datastore']
], scope="module")


@pytest.yield_fixture(scope="function")
def tagcontrol_dialog(appliance):
    service_dialogs = DialogCollection(appliance)
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data = {
        'ele_label': "Service Level",
        'ele_name': "service_level",
        'ele_desc': "service_level_desc",
        'choose_type': "Tag Control",
        'field_category': "Service Level",
        'field_required': True
    }
    sd = service_dialogs.create(label=dialog,
        description="my dialog", submit=True, cancel=True,)
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label='box_' + fauxfactory.gen_alphanumeric(),
        box_desc="my box desc")
    box.elements.create(element_data=[element_data])
    yield sd


@pytest.yield_fixture(scope="function")
def catalog():
    catalog = "cat_" + fauxfactory.gen_alphanumeric()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    yield cat


@pytest.fixture(scope="function")
def catalog_item(provider, provisioning, vm_name, tagcontrol_dialog, catalog):
    template, host, datastore, iso_file, catalog_item_type, vlan = map(provisioning.get,
        ('template', 'host', 'datastore', 'iso_file', 'catalog_item_type', 'vlan'))

    provisioning_data = {
        'catalog': {'vm_name': vm_name,
                    },
        'environment': {'host_name': {'name': host},
                        'datastore_name': {'name': datastore},
                        },
        'network': {'vlan': vlan,
                    },
    }

    if provider.type == 'rhevm':
        provisioning_data['catalog']['provision_type'] = 'Native Clone'
    elif provider.type == 'virtualcenter':
        provisioning_data['catalog']['provision_type'] = 'VMware'
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=tagcontrol_dialog, catalog_name=template,
                  provider=provider, prov_data=provisioning_data)
    return catalog_item


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(blockers=[BZ(1434990, forced_streams=["5.7", "upstream"])])
def test_tagdialog_catalog_item(appliance, provider, setup_provider, catalog_item, request):
    """Tests tag dialog catalog item
    Metadata:
        test_flag: provision
    """
    vm_name = catalog_item.provisioning_data['catalog']["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    catalog_item.create()
    dialog_values = {
        'default_select_value': "Gold"
    }
    service_catalogs = ServiceCatalogs(appliance, catalog=catalog_item.catalog,
                                       name=catalog_item.name,
                                       dialog_values=dialog_values)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    assert provision_request.is_succeeded()
