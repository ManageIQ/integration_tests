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
from cfme.utils.net import find_pingable
from cfme.utils.rest import delete_resources_from_collection
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


@pytest.fixture(scope="function")
def ansible_scm_credentials(appliance, wait_for_ansible):
    """
    This fixture will add git SCM credentials which used to add private git repositories.
    """
    # Check for the SCM credentials key from yaml.
    credentials_collection = appliance.collections.ansible_credentials
    try:
        creds = {
            "username": credentials["scm_creds"]["username"],
            "password": credentials["scm_creds"]["password"],
        }
    # Create SCM credentails.
        scm_credential = credentials_collection.create("Scm_credential", "Scm", **creds)
    except (KeyError, AttributeError):
        message = "Missing 'SCM credentails' key in cfme_data, cannot add SCM credentials."
        logger.exception(message)  # log the exception for debug of the missing content
        pytest.skip(message)

    yield scm_credential

    scm_credential.delete_if_exists()


@pytest.fixture(scope="function")
def ansible_private_repository(request, appliance, ansible_scm_credentials):
    """
    Ansible Repository fixture will be used to create SCM repositories by using SCM credentials.
    """
    repositories = appliance.collections.ansible_repositories
    try:
        playbooks_yaml = cfme_data.ansible_links.private_repository
        playbook_name = getattr(request, 'param', 'private_repo')
        repository = repositories.create(
            name=fauxfactory.gen_alpha(),
            url=getattr(playbooks_yaml, playbook_name),
            description=fauxfactory.gen_alpha(),
            scm_credentials=ansible_scm_credentials.name,
        )
    except (KeyError, AttributeError):
        message = "Missing ansible_links content in cfme_data, cannot setup repository"
        logger.exception(message)  # log the exception for debug of the missing content
        pytest.skip(message)
    view = navigate_to(repository, "Details")
    wait_for(
        lambda: repository.status == "successful",
        num_sec=120,
        delay=2,
        fail_func=view.toolbar.refresh.click
    )

    yield repository

    repository.delete_if_exists()


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
def ansible_catalog(appliance, ansible_catalog_item):
    catalog = appliance.collections.catalogs.create(fauxfactory.gen_alphanumeric(),
                                                    description="my ansible catalog",
                                                    items=[ansible_catalog_item.name])
    ansible_catalog_item.catalog = catalog
    yield catalog

    if catalog.exists:
        catalog.delete()
        ansible_catalog_item.catalog = None


@pytest.fixture(scope="function")
def ansible_service_catalog(appliance, ansible_catalog_item, ansible_catalog):
    service_catalog = ServiceCatalogs(appliance, ansible_catalog, ansible_catalog_item.name)
    return service_catalog


def bulk_service_teardown(appliance):
    """Delete all service requests on the appliance via rest"""
    # big diaper here because of service requests having the same description
    requests = [r for r in appliance.rest_api.collections.service_requests]
    if requests:
        delete_resources_from_collection(
            resources=requests,
            collection=appliance.rest_api.collections.service_requests,
            check_response=False
        )


@pytest.fixture(scope="function")
def ansible_service_request(appliance, ansible_catalog_item):
    """
    This fixture is VERY aggressive in teardown, and deletes ALL service requests on the appliance
    """
    request_descr = (f"Provisioning Service [{ansible_catalog_item.name}] "
                     f"from [{ansible_catalog_item.name}]")
    service_request = appliance.collections.requests.instantiate(description=request_descr)
    yield service_request

    bulk_service_teardown(appliance)


@pytest.fixture(scope="function")
def ansible_service(appliance, ansible_catalog_item):
    service = MyService(appliance, ansible_catalog_item.name)
    yield service

    bulk_service_teardown(appliance)  # deletes any service requests
    if service.exists:
        service.delete()


@pytest.fixture(scope="function")
def order_ansible_service_in_ops_ui(appliance, ansible_catalog_item,
                                    ansible_service_catalog):
    """Orders an ansible service through the UI
    Deletes the service request after completion, as well as the service
    """
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


@pytest.fixture(scope="function")
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
    """Fixture to provide target machine for ansible testing. It will not teardown crated Machine"""

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
        hostname, _ = wait_for(
            find_pingable, func_args=[vm.mgmt], timeout="10m", delay=5, fail_condition=None
        )
    except TimedOutError:
        pytest.skip(
            f"Timed out: waiting for pingable ip for Target Machine: {vm.name} on '{provider.name}"
        )

    yield TargetMachine(
        vm=vm,
        hostname=hostname,
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
