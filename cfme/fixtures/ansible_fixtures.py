from collections import namedtuple

import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.net import wait_pingable
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

TargetMachine = namedtuple("TargetMachine", ["vm", "hostname", "username", "password"])


@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.server.settings.enable_server_roles("embedded_ansible")
    appliance.wait_for_embedded_ansible()
    yield
    appliance.server.settings.disable_server_roles("embedded_ansible")


@pytest.fixture(scope="module")
def ansible_repository(request, appliance, wait_for_ansible):
    """
    By default cfme_data.ansible_links.playbook_repositories.embedded_ansible is set for the url,
    but you can specify it explicitly with @pytest.mark.parametrize decorator on your test function.

    Example:
    @pytest.mark.parametrize('ansible_repository', ['nuage'], indirect=True)
    def test_function(ansible_repository):
        ...
    """
    repositories = appliance.collections.ansible_repositories
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

    repository.delete_if_exists()


@pytest.fixture(scope="module")
def ansible_catalog_item(appliance, ansible_repository):
    collection = appliance.collections.catalog_items
    cat_item = collection.create(
        collection.ANSIBLE_PLAYBOOK,
        fauxfactory.gen_alphanumeric(),
        fauxfactory.gen_alphanumeric(),
        display_in_catalog=True,
        provisioning={
            "repository": ansible_repository.name,
            "playbook": "dump_all_variables.yml",
            "machine_credential": "CFME Default Credential",
            "create_new": True,
            "provisioning_dialog_name": fauxfactory.gen_alphanumeric(),
            "extra_vars": [("some_var", "some_value")]
        },
        retirement={
            "repository": ansible_repository.name,
            "playbook": "dump_all_variables.yml",
            "machine_credential": "CFME Default Credential",
            "extra_vars": [("some_var", "some_value")]
        }
    )
    yield cat_item

    cat_item.delete_if_exists()


@pytest.fixture(scope="module")
def ansible_catalog(appliance, ansible_catalog_item):
    catalog = appliance.collections.catalogs.create(fauxfactory.gen_alphanumeric(),
                                                    description="my ansible catalog",
                                                    items=[ansible_catalog_item.name])
    ansible_catalog_item.catalog = catalog
    yield catalog

    if catalog.exists:
        catalog.delete()
        ansible_catalog_item.catalog = None


@pytest.fixture(scope="module")
def ansible_service_catalog(appliance, ansible_catalog_item, ansible_catalog):
    service_catalog = ServiceCatalogs(appliance, ansible_catalog, ansible_catalog_item.name)
    return service_catalog


@pytest.fixture(scope="function")
def ansible_service_request_funcscope(appliance, ansible_catalog_item):
    request_descr = "Provisioning Service [{0}] from [{0}]".format(ansible_catalog_item.name)
    service_request = appliance.collections.requests.instantiate(description=request_descr)
    yield service_request

    if service_request.exists():
        service_id = appliance.rest_api.collections.service_requests.get(description=request_descr)
        appliance.rest_api.collections.service_requests.action.delete(id=service_id.id)


@pytest.fixture(scope="function")
def ansible_service_funcscope(appliance, ansible_catalog_item):
    service = MyService(appliance, ansible_catalog_item.name)
    yield service

    if service.exists:
        service.delete()


@pytest.fixture(scope="module")
def ansible_service_request(appliance, ansible_catalog_item):
    request_descr = "Provisioning Service [{0}] from [{0}]".format(ansible_catalog_item.name)
    service_request = appliance.collections.requests.instantiate(description=request_descr)
    yield service_request

    if service_request.exists():
        service_id = appliance.rest_api.collections.service_requests.get(description=request_descr)
        appliance.rest_api.collections.service_requests.action.delete(id=service_id.id)


@pytest.fixture(scope="module")
def ansible_service(appliance, ansible_catalog_item):
    service = MyService(appliance, ansible_catalog_item.name)
    yield service

    if service.exists:
        service.delete()


@pytest.fixture(scope="module")
def order_ansible_service_in_ops_ui(appliance, ansible_catalog_item,
                                    ansible_service_catalog):
    """Tests if ansible playbook service provisioning is shown in service requests."""
    ansible_service_catalog.order()
    cat_item_name = ansible_catalog_item.name
    request_descr = "Provisioning Service [{0}] from [{0}]".format(cat_item_name)
    service_request = appliance.collections.requests.instantiate(description=request_descr)
    if service_request.exists():
        service_request.wait_for_request()
        if not BZ(1646333, forced_streams=['5.10']).blocks:
            service_request.remove_request()
    yield cat_item_name
    service = MyService(appliance, cat_item_name)
    if service.exists:
        service.delete()


@pytest.fixture(scope="module")
def ansible_catalog_item_create_empty_file(appliance, ansible_repository):
    collection = appliance.collections.catalog_items
    cat_item = collection.create(
        collection.ANSIBLE_PLAYBOOK,
        fauxfactory.gen_alphanumeric(15, start="create_file_"),
        fauxfactory.gen_alphanumeric(start="disc_"),
        display_in_catalog=True,
        provisioning={
            "repository": ansible_repository.name,
            "playbook": "create_empty_file.yml",
            "machine_credential": "CFME Default Credential",
            "create_new": True,
            "provisioning_dialog_name": fauxfactory.gen_alphanumeric(15, start="ansi_dialog_"),
        },
    )
    catalog = appliance.collections.catalogs.create(
        fauxfactory.gen_alphanumeric(start="cat_"),
        description=fauxfactory.gen_alphanumeric(start="cat_dis_"),
        items=[cat_item.name],
    )

    yield cat_item
    catalog.delete_if_exists()
    cat_item.delete_if_exists()


@pytest.fixture(scope="module")
def target_machine(provider, setup_provider_modscope):
    """Fixture to provide target machine for ansible testing"""
    try:
        target_data = provider.data.ansible_target
    except AttributeError:
        pytest.skip(f"Could not find 'ansible_target' tag in provider yaml: '{provider.name}'")

    vm = provider.appliance.provider_based_collection(provider).instantiate(
        target_data.name, provider, target_data.template
    )

    if not provider.mgmt.does_vm_exist(target_data.name):
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")

    # For OSP provider need to assign floating ip
    if provider.one_of(OpenStackProvider):
        public_net = provider.data["public_network"]
        vm.mgmt.assign_floating_ip(public_net)

    # wait for pingable ip address
    try:
        wait_pingable(vm.mgmt, wait=600)
    except TimedOutError:
        pytest.skip(f"Timed out waiting for pingable address on Target Machine: {vm.name}")

    yield TargetMachine(
        vm=vm,
        hostname=vm.ip_address,
        username=credentials[target_data.credentials].username,
        password=credentials[target_data.credentials].password,
    )


@pytest.fixture(scope="module")
def target_machine_ansible_creds(appliance, target_machine):
    creds = appliance.collections.ansible_credentials.create(
        name=fauxfactory.gen_alpha(start="cred_"),
        credential_type="Machine",
        username=target_machine.username,
        password=target_machine.password,
    )
    yield creds
    creds.delete_if_exists()
