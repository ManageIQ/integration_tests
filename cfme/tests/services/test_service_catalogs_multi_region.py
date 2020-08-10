from urllib.parse import urlparse

import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.fixtures.ansible_tower import ansible_tower_dialog_rest
from cfme.infrastructure.config_management.ansible_tower import AnsibleTowerProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.rest.gen_data import dialog as _dialog
from cfme.rest.gen_data import service_catalog_obj as _catalog
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI
from cfme.utils.generators import random_vm_name
from cfme.utils.update import update
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.long_running,
    pytest.mark.provider([CloudProvider, InfraProvider],
        required_fields=[
            ['provisioning', 'template'],
            ['provisioning', 'host'],
            ['provisioning', 'datastore'],
            ['provisioning', 'vlan']],
        scope='module')
]


@pytest.fixture
def remote_appliance(replicated_appliances):
    return replicated_appliances[0]


@pytest.fixture
def remote_catalog(request, remote_appliance):
    return _catalog(request, remote_appliance)


@pytest.fixture
def remote_dialog(request, remote_appliance):
    service_dialog = _dialog(request, remote_appliance)

    yield service_dialog

    with remote_appliance:
        service_dialog.delete_if_exists()


@pytest.fixture
def remote_ansible_tower_dialog(request, remote_appliance):
    """Create and return a service dialog object."""
    with remote_appliance:
        rest_resource = ansible_tower_dialog_rest(request, remote_appliance)
        service_dialog = remote_appliance.collections.service_dialogs.instantiate(
            label=rest_resource.label, description=rest_resource.description)

    yield service_dialog

    with remote_appliance:
        service_dialog.delete_if_exists()


@pytest.fixture
def setup_remote_provider(provider, remote_appliance):
    with remote_appliance:
        provider.create(validate_inventory=True)


@pytest.fixture
def remote_catalog_item(remote_appliance, provider, setup_remote_provider, remote_catalog,
                        remote_dialog, provisioning_data):
    with remote_appliance:
        catalog_item = remote_appliance.collections.catalog_items.create(
            provider.catalog_item_type,
            name=fauxfactory.gen_alphanumeric(15, start="cat_item_"),
            description="my catalog",
            display_in=True,
            catalog=remote_catalog,
            dialog=remote_dialog,
            prov_data=provisioning_data)

    yield catalog_item

    with remote_appliance:
        catalog_item.delete_if_exists()


@pytest.fixture
def remote_ansible_api_version_change(remote_appliance, provider, ansible_api_version):
    """Update Ansible Tower provider URL to /api/{ansible_api_version} so that all supported API
    versions can be tested.
    """
    original_url = provider.url
    parsed = urlparse(provider.url)
    updated_url = f'{parsed.scheme}://{parsed.netloc}/api/{ansible_api_version}'

    with remote_appliance:
        with update(provider, validate_credentials=True):
            provider.url = updated_url

    yield

    with remote_appliance:
        with update(provider, validate_credentials=True):
            provider.url = original_url


@pytest.fixture
def remote_ansible_catalog_item(remote_appliance, provider, setup_remote_provider, remote_catalog,
                                remote_dialog):
    provider_name = provider.data['name']
    template = provider.data['provisioning_data']['template']
    with remote_appliance:
        catalog_item = remote_appliance.collections.catalog_items.create(
            remote_appliance.collections.catalog_items.ANSIBLE_TOWER,
            name=remote_dialog.label,
            description="my catalog",
            display_in=True,
            catalog=remote_catalog,
            dialog=remote_dialog,
            provider=f'{provider_name} Automation Manager',
            config_template=template)

    yield catalog_item

    with remote_appliance:
        catalog_item.delete_if_exists()


@pytest.fixture
def provisioning_data(provisioning, provider):
    return {
        'catalog': {
            'catalog_name': {'name': provisioning.template, 'provider': provider.name},
            'vm_name': random_vm_name('service')
        },
        'environment': {
            'host_name': {'name': provisioning.host},
            'datastore_name': {'name': provisioning.datastore}
        },
        'network': {'vlan': partial_match(provisioning.vlan)},
    }


def _order_retire_service(
        request, provider, context, appliance, catalog_item):
    """Common code to order and then retire a service."""
    with appliance:
        # Order the service
        provision_request = ServiceCatalogs(
            appliance, catalog_item.catalog, catalog_item.name).order()

        provision_request.wait_for_request(method='ui')
        assert provision_request.is_succeeded(method='ui')

        service = MyService(appliance, catalog_item.name)

        @request.addfinalizer
        def _clear_request_service():
            if provision_request.exists():
                provision_request.remove_request()
            if service.exists:
                service.delete()

        assert service.exists

        # Retire the service via UI or REST, depending on context
        if context == ViaUI:
            retire_request = service.retire()
            assert retire_request and retire_request.exists()
        else:
            # TODO: implement retire() via REST using sentaku context
            services = appliance.rest_api.collections.services
            api_service = services.get(name=service.name)
            api_retire_requests = services.action.request_retire(api_service)
            assert len(api_retire_requests) == 1
            api_retire_request = api_retire_requests[0]
            assert api_retire_request and api_retire_request.exists
            retire_request = appliance.collections.requests.instantiate(
                f'Service Retire for: {service.name}')

        @request.addfinalizer
        def _remove_retire_request():
            retire_request.remove_request()

        wait_for(lambda: service.is_retired, delay=5, num_sec=300,
            fail_func=service.browser.refresh, message="Waiting for service to retire")


@pytest.mark.tier(2)
@test_requirements.multi_region
@test_requirements.service
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
def test_service_provision_retire_from_global_region(
        request, provider, context, replicated_appliances, remote_catalog_item):
    """From the global appliance in a multi-region appliance configuration, order and then retire
    a VM provisioning service on the remote appliance.

    Polarion:
        assignee: tpapaioa
        caseimportance: high
        casecomponent: Services
        initialEstimate: 1/3h
    """
    _, global_appliance = replicated_appliances
    _order_retire_service(request, provider, context, global_appliance, remote_catalog_item)

    vm_name = f"{remote_catalog_item.prov_data['catalog']['vm_name']}0001"
    vm = global_appliance.provider_based_collection(provider).instantiate(vm_name, provider)
    assert vm.wait_for_vm_state_change(from_any_provider=True, desired_state='archived')


@pytest.mark.tier(2)
@test_requirements.multi_region
@test_requirements.service
@pytest.mark.provider([AnsibleTowerProvider], scope='module')
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.parametrize('ansible_api_version', ['v2'])
def test_service_provision_retire_from_global_region_ansible_tower(
        request, provider, context, replicated_appliances, remote_ansible_catalog_item,
        remote_ansible_api_version_change):
    """
    Polarion:
        assignee: tpapaioa
        caseimportance: high
        casecomponent: Services
        initialEstimate: 1/3h
        testSteps:
            1. Take two or more appliances
            2. Configure DB manually
            3. Make one appliance as Global region and second are Remote
            4. Add appropriate provider to remote region appliance
            5. Create Dialog
            6. Create Catalog
            7. Create Catalog Item of above provider type in remote appliance
            8. Order appearing service catalog in global appliance
            9. Retire provisioned service in global appliance

        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7.
            8. service catalog has been successfully provisioned
            9. service has been successfully retired
    """
    _, global_appliance = replicated_appliances
    _order_retire_service(
        request, provider, context, global_appliance, remote_ansible_catalog_item)


@pytest.mark.manual
@pytest.mark.tier(2)
@test_requirements.multi_region
@test_requirements.service
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.parametrize('catalog_location', ['remote'])  # TODO add global
@pytest.mark.parametrize('item_type', ['ansible', 'generic', 'orchestration', 'bundle'])
def test_service_provision_retire_from_global_region_manual(item_type, catalog_location, context):
    """
    Polarion:
        assignee: tpapaioa
        caseimportance: high
        casecomponent: Services
        initialEstimate: 1/3h
        testSteps:
            1. Take two or more appliances
            2. Configure DB manually
            3. Make one appliance as Global region and second are Remote
            4. Add appropriate provider to remote region appliance
            5. Create Dialog
            6. Create Catalog
            7. Create Catalog Item of above provider type in remote appliance
            8. Order appearing service catalog in global appliance
            9. Retire provisioned service in global appliance

        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7.
            8. service catalog has been successfully provisioned
            9. service has been successfully retired
    """
    pass
