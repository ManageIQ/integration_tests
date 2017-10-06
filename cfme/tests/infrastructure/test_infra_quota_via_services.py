# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.blockers import BZ
from cfme.utils.update import update
from cfme.utils import testgen

pytestmark = [
    test_requirements.quota,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers')
]


vm_name = 'test_quota_prov_{}'.format(fauxfactory.gen_alphanumeric())


pytest_generate_tests = testgen.generate(
    [VMwareProvider], required_fields=[['provisioning', 'template']], scope="module")


@pytest.fixture(scope="function")
def template_name(provisioning):
    return provisioning["template"]


@pytest.fixture(scope='module')
def test_domain(appliance):
    domain = appliance.collections.domains.create('test_' + fauxfactory.gen_alphanumeric(),
                                                  'description_' + fauxfactory.gen_alphanumeric(),
                                                  enabled=True)
    yield domain
    domain.delete()


@pytest.fixture(scope='module')
def max_quota_test_instance(appliance, test_domain):
    miq = appliance.collections.domains.instantiate('ManageIQ')

    original_instance = miq.\
        namespaces.instantiate('Cloud').\
        namespaces.instantiate('VM').\
        namespaces.instantiate('Provisioning').\
        namespaces.instantiate('StateMachines').\
        classes.instantiate('ProvisionRequestApproval').\
        instances.instantiate('Default')
    original_instance.copy_to(domain=test_domain)

    instance = test_domain.\
        namespaces.instantiate('Cloud'). \
        namespaces.instantiate('VM'). \
        namespaces.instantiate('Provisioning'). \
        namespaces.instantiate('StateMachines'). \
        classes.instantiate('ProvisionRequestApproval'). \
        instances.instantiate('Default')

    yield instance
    instance.delete()


@pytest.fixture(scope='function')
def max_field_method(request, max_quota_test_instance):
    field, value = request.param
    with update(max_quota_test_instance):
        max_quota_test_instance.fields = { field: {'value': value} }
    yield
    with update(max_quota_test_instance):
        max_quota_test_instance.fields = { field: {'value': ''} }


def create_dialog(appliance, element_data, label=None):
    if label is None:
        label = 'label_' + fauxfactory.gen_alphanumeric()
    sd = appliance.collections.service_dialogs.create(label=label,
        description="my dialog", submit=True, cancel=True)
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label='box_' + fauxfactory.gen_alphanumeric(),
        box_desc="my box desc")
    box.elements.create(element_data=[element_data])
    return sd


@pytest.fixture(scope='module')
def dialog_with_field(request, appliance):
    field = request.param
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': field,
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    dialog = create_dialog(appliance, element_data)
    yield dialog
    dialog.delete()


def vmware_catalog_item(provider, vm_name, template, catalog, number_of_vms_dialog, prov_data):
    prov_data['environment'] = {'automatic_placement': True}
    catalog_item = CatalogItem(item_type='VMware',
                               name=fauxfactory.gen_alphanumeric(),
                               description="my catalog",
                               display_in=True,
                               provider=provider,
                               catalog=catalog,
                               catalog_name=template,
                               dialog=number_of_vms_dialog,
                               prov_data=prov_data)
    catalog_item.create()
    return catalog_item

@pytest.mark.meta(blockers=[BZ(1497912, forced_streams=['5.7', '5.8', '5.9', 'upstream'])])
@pytest.mark.parametrize(
    ['max_field_method', 'dialog_with_field', 'prov_data'],
    [
        [('max_vms', '1'), 'number_of_vms', {'catalog': {'vm_name': vm_name, 'num_vms': '2'}}],
        [('max_cpus', '1'), 'number_of_sockets', {'catalog': {'vm_name': vm_name},
                                                  'hardware': {'num_sockets': '2'}}]
    ],
    indirect=['max_field_method', 'dialog_with_field'],
    ids=['max_vms', 'max_cpus'])
def test_quota_via_custom_dialog(appliance, provider, setup_provider,
                                 vm_name, template_name, catalog,
                                 max_field_method, dialog_with_field, prov_data):
    catalog_item = vmware_catalog_item(provider, vm_name, template_name,
                                       catalog, dialog_with_field, prov_data)
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog,
                                       catalog_item.name)
    service_catalogs.order()
    request_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.approve_request(method='ui', reason="Approved")
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.reason.text == "Quota Exceeded"
