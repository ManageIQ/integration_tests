import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.generators import random_vm_name
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.long_running,
    test_requirements.service,
    pytest.mark.tier(2),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, scope="module"),
]


@pytest.fixture(scope="function")
def catalog_item_setups(appliance, provider, provisioning, request, catalog, dialog):
    """
    This fixture is used to create two catalog items instance pointing to method
    """
    template, host, datastore, vlan = list(map(
        provisioning.get, ('template', 'host', 'datastore', 'vlan'))
    )
    provisioning_data = {
        'catalog': {'catalog_name': {'name': template, 'provider': provider.name},
                    'vm_name': random_vm_name('service')},
        'environment': {'host_name': {'name': host},
                        'datastore_name': {'name': datastore}},
        'network': {'vlan': partial_match(vlan)},
    }
    cat_list = []
    for i in range(2):

        catalog_item = appliance.collections.catalog_items.create(
            provider.catalog_item_type,
            name=fauxfactory.gen_alphanumeric(15, start="cat_item_"),
            description="my catalog",
            display_in=True,
            catalog=catalog,
            dialog=dialog,
            prov_data=provisioning_data
        )

        collection = provider.appliance.provider_based_collection(provider)
        vm_name1 = "{}0001".format(catalog_item.prov_data["catalog"]["vm_name"])
        vm_name2 = "{}0002".format(catalog_item.prov_data["catalog"]["vm_name"])
        vm1 = collection.instantiate("{}".format(vm_name1), provider)
        vm2 = collection.instantiate("{}".format(vm_name2), provider)

        cat_list.append(catalog_item)
        request.addfinalizer(cat_list[i].delete_if_exists)

    yield catalog_item, cat_list, vm1, vm2


@pytest.mark.meta(coverage=[1654165])
@pytest.mark.tier(2)
def test_retire_service_and_bundle_vms(request, appliance, catalog_item_setups):
    """
    Bugzilla:
        1654165

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/6h
        startsin: 5.10
        testSteps:
            1. Create catalog and create two catalog items
            2. Create bundle with above two catalog items
            3. Order the catalog bundle
            4. Go to My services
            5. Check the Both VMs
            6. Retire the services
        expectedResults:
            1.
            2.
            3.
            4.
            5. Both VMs should be present
            6. Services should retire and vms as well
    """
    catalog_item, cat_list, vm1, vm2 = catalog_item_setups

    # Creating catalog bundle of two catalog items
    catalog_bundle = appliance.collections.catalog_bundles.create(
        name=fauxfactory.gen_alphanumeric(),
        description="catalog_bundle",
        display_in=True,
        catalog=catalog_item.catalog,
        dialog=catalog_item.dialog,
        catalog_items=[cat_list[0].name, cat_list[1].name],
    )
    request.addfinalizer(catalog_bundle.delete_if_exists)

    # Ordering service catalog bundle
    service_catalogs = ServiceCatalogs(
        appliance, catalog_bundle.catalog, catalog_bundle.name
    )
    service_catalogs.order()
    request_description = (
        f'Provisioning Service [{catalog_bundle.name}] from [{catalog_bundle.name}]'
    )

    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    provision_request.is_succeeded(method="ui")
    service = MyService(appliance, catalog_item.dialog.label)

    @request.addfinalizer
    def _clear_request_service():
        if provision_request.exists():
            provision_request.remove_request(method="rest")
        if service.exists:
            service.delete()

    assert service.exists

    # Retire service
    retire_request = service.retire()
    assert retire_request.exists()

    @request.addfinalizer
    def _clear_retire_request():
        if retire_request.exists():
            retire_request.remove_request()

    wait_for(
        lambda: service.is_retired,
        delay=5, num_sec=120,
        fail_func=service.browser.refresh,
        message="waiting for service retire"
    )
    assert vm1.wait_for_vm_state_change(from_any_provider=True, desired_state='archived')
    assert vm2.wait_for_vm_state_change(from_any_provider=True, desired_state='archived')
