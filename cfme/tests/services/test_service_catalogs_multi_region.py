from urllib.parse import urlparse

import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.fixtures.ansible_tower import ansible_tower_dialog_rest
from cfme.infrastructure.config_management.ansible_tower import AnsibleTowerProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.rest.gen_data import dialog as _dialog
from cfme.rest.gen_data import service_catalog_obj as _catalog
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import cfme_data
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
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

# TODO: Define a single fixture to create catalog_item, since there is only a minor difference
#       between all the fixtures that create catalog_item.


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
def remote_embedded_ansible_dialog(request, remote_appliance):
    service_dialog = _dialog(request, remote_appliance)

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
def remote_generic_catalog_item(remote_appliance, remote_catalog, remote_dialog):
    with remote_appliance:
        catalog_item = remote_appliance.collections.catalog_items.create(
            remote_appliance.collections.catalog_items.GENERIC,
            name=fauxfactory.gen_alphanumeric(15, start="cat_item_"),
            description="my catalog",
            display_in=True,
            catalog=remote_catalog,
            dialog=remote_dialog,
        )

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
def remote_ansible_credentials(remote_appliance, provider, setup_provider_modscope):
    provider_credentials = provider.get_credentials_from_config(provider.data['credentials'])
    cred_type = 'VMware'
    with remote_appliance:
        ansible_credentials = remote_appliance.collections.ansible_credentials.create(
            f"{cred_type}_cred_{fauxfactory.gen_alpha()}",
            cred_type,
            username=provider_credentials.principal,
            password=provider_credentials.secret,
            vcenter_host=provider.hostname
        )

    yield ansible_credentials

    with remote_appliance:
        ansible_credentials.delete_if_exists()


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
def remote_ansible_repository(request, remote_appliance, wait_for_ansible):
    with remote_appliance:
        repositories = remote_appliance.collections.ansible_repositories
        try:
            playbooks_yaml = cfme_data.ansible_links.playbook_repositories
            playbook_name = getattr(request, 'param', 'embedded_ansible')
            repository = repositories.create(
                name=fauxfactory.gen_alpha(),
                url=getattr(playbooks_yaml, playbook_name),
                description=fauxfactory.gen_alpha()
            )
        except (KeyError, AttributeError):
            message = "Missing ansible_links content in cfme_data, cannot setup repository"
            logger.exception(message)  # log the exception for debug of the missing content
            pytest.skip(message)
        view = navigate_to(repository, "Details")
        wait_for(
            lambda: view.entities.summary("Properties").get_text_of("Status") == "successful",
            timeout=60,
            fail_func=view.toolbar.refresh.click
        )
        yield repository

    with remote_appliance:
        repository.delete_if_exists()


@pytest.fixture
def wait_for_ansible(remote_appliance):
    remote_appliance.server.settings.enable_server_roles("embedded_ansible")
    remote_appliance.wait_for_embedded_ansible()
    yield
    remote_appliance.server.settings.disable_server_roles("embedded_ansible")


@pytest.fixture
def remote_embedded_ansible_catalog_item(
        setup_remote_provider, remote_appliance, remote_catalog,
        remote_embedded_ansible_dialog, remote_ansible_repository, remote_ansible_credentials):
    collection = remote_appliance.collections.catalog_items
    with remote_appliance:
        catalog_item = collection.create(
            collection.ANSIBLE_PLAYBOOK,
            name=remote_embedded_ansible_dialog.label,
            description="my catalog",
            display_in_catalog=True,
            catalog=remote_catalog,
            provisioning={
                'repository': remote_ansible_repository.name,
                'playbook': 'gather_all_vms_from_vmware.yml',
                'machine_credential': 'CFME Default Credential',
                'cloud_type': 'VMware',
                'cloud_credential': remote_ansible_credentials.name,
                'create_new': True,
                'provisioning_dialog_name': 'some_dialog'
            }
        )

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


def order_retire_service(request, context, appliance, catalog_item):
    """Common method to order and then retire a service."""
    with appliance:
        # Order the service
        provision_request = ServiceCatalogs(
            appliance, catalog=catalog_item.catalog, name=catalog_item.name
        ).order()
        provision_request.wait_for_request(method='ui')
        assert provision_request.is_succeeded(method='ui')
        if isinstance(catalog_item, appliance.collections.catalog_items.GENERIC):
            service_name = catalog_item.dialog.label
        else:
            service_name = catalog_item.name
        service = MyService(appliance, service_name)

        @request.addfinalizer
        def _clear_request_service():
            if provision_request.exists():
                provision_request.remove_request()
            if service.exists:
                service.delete()

        assert service.exists

        # Retire the service via UI or REST, depending on context
        with appliance.context.use(context):
            retire_request = service.retire()
            assert retire_request and retire_request.exists()

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
    """Order and retire a cloud or infrastructure provider service from the global appliance.

    Polarion:
        assignee: tpapaioa
        caseimportance: high
        casecomponent: Services
        initialEstimate: 1/3h
    """
    _, global_appliance = replicated_appliances
    order_retire_service(request, context, global_appliance, remote_catalog_item)

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
    """Order and retire an Ansible Tower service from the global appliance.

    Polarion:
        assignee: tpapaioa
        caseimportance: high
        casecomponent: Services
        initialEstimate: 1/3h
    """
    _, global_appliance = replicated_appliances
    order_retire_service(request, context, global_appliance, remote_ansible_catalog_item)


@pytest.mark.tier(2)
@test_requirements.multi_region
@test_requirements.service
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.provider([VMwareProvider], scope='module')
def test_service_provision_retire_from_global_region_embedded_ansible(
        request, context, replicated_appliances, setup_remote_provider,
        remote_embedded_ansible_catalog_item):
    """Order and retire an embedded Ansible playbook service from the global appliance,
    against the default host.

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Ansible
        caseimportance: high
    """
    _, global_appliance = replicated_appliances
    order_retire_service(
        request, context, global_appliance, remote_embedded_ansible_catalog_item)


@pytest.mark.parametrize("context", [ViaREST, ViaUI])
def test_service_provision_retire_from_global_region_generic(
    request, context, replicated_appliances, remote_generic_catalog_item
):
    """Order and retire a Generic service from the global appliance.
    Polarion:
        assignee: tpapaioa
        caseimportance: high
        casecomponent: Services
        initialEstimate: 1/3h
    """
    _, global_appliance = replicated_appliances
    order_retire_service(request, context, global_appliance, remote_generic_catalog_item)


@pytest.mark.manual
@pytest.mark.tier(2)
@test_requirements.multi_region
@test_requirements.service
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.parametrize('catalog_location', ['remote'])  # TODO add global
@pytest.mark.parametrize('item_type', ['ansible', 'orchestration', 'bundle'])
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
