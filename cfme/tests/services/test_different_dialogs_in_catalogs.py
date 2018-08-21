# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.blockers import GH
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger

pytestmark = [
    pytest.mark.meta(server_roles="+automate", blockers=[GH('ManageIQ/integration_tests:7479')]),
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.usefixtures('setup_provider', 'catalog_item', 'uses_infra_providers'),
    test_requirements.service,
    pytest.mark.long_running,
    pytest.mark.provider([InfraProvider],
                         required_fields=[['provisioning', 'template'],
                                          ['provisioning', 'host'],
                                          ['provisioning', 'datastore']],
                         scope="module")
]


@pytest.fixture(scope="function")
def tagcontrol_dialog(appliance):
    service_dialog = appliance.collections.service_dialogs
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data = {
        'element_information': {
            'ele_label': "Service Level",
            'ele_name': "service_level",
            'ele_desc': "service_level_desc",
            'choose_type': "Tag Control",
        },
        'options': {
            'field_category': "Service Level",
            'field_required': True
        }
    }
    sd = service_dialog.create(label=dialog, description="my dialog")
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label='box_' + fauxfactory.gen_alphanumeric(),
        box_desc="my box desc")
    box.elements.create(element_data=[element_data])
    yield sd


@pytest.fixture(scope="function")
def catalog(appliance):
    catalog = "cat_" + fauxfactory.gen_alphanumeric()
    cat = appliance.collections.catalogs.create(name=catalog, description="my catalog")
    yield cat


@pytest.fixture(scope="function")
def catalog_item(appliance, provider, provisioning, tagcontrol_dialog, catalog):
    template, host, datastore, iso_file, vlan = map(provisioning.get,
        ('template', 'host', 'datastore', 'iso_file', 'vlan'))

    provisioning_data = {
        'catalog': {'catalog_name': {'name': template, 'provider': provider.name},
                    'vm_name': random_vm_name('service')},
        'environment': {'host_name': {'name': host},
                        'datastore_name': {'name': datastore}},
        'network': {'vlan': partial_match(vlan)},
    }

    if provider.type == 'rhevm':
        provisioning_data['catalog']['provision_type'] = 'Native Clone'
    elif provider.type == 'virtualcenter':
        provisioning_data['catalog']['provision_type'] = 'VMware'
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = appliance.collections.catalog_items.create(
        provider.catalog_item_type,
        name=item_name,
        description="my catalog",
        display_in=True,
        catalog=catalog,
        dialog=tagcontrol_dialog,
        prov_data=provisioning_data)
    return catalog_item


@pytest.mark.rhv2
@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_tagdialog_catalog_item(appliance, provider, catalog_item, request):
    """Tests tag dialog catalog item
    Metadata:
        test_flag: provision
    """
    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            "{}0001".format(vm_name), provider).cleanup_on_provider()
    )
    dialog_values = {'service_level': "Gold"}
    service_catalogs = ServiceCatalogs(appliance, catalog=catalog_item.catalog,
                                       name=catalog_item.name,
                                       dialog_values=dialog_values)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = "Request failed with the message {}".format(provision_request.rest.message)
    assert provision_request.is_succeeded(), msg
