import fauxfactory
import pytest

from cfme.services.catalogs.catalog import Catalog
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.myservice import MyService
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import cfme_data
from cfme.utils.wait import wait_for


@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.server.settings.enable_server_roles("embedded_ansible")
    appliance.wait_for_embedded_ansible()
    yield
    appliance.server.settings.disable_server_roles("embedded_ansible")


@pytest.fixture(scope="module")
def ansible_repository(appliance, wait_for_ansible):
    repositories = appliance.collections.ansible_repositories
    try:
        repository = repositories.create(
            name=fauxfactory.gen_alpha(),
            url=cfme_data.ansible_links.playbook_repositories.embedded_ansible,
            description=fauxfactory.gen_alpha())
    except KeyError:
        pytest.skip("Skipping since no such key found in yaml")
    view = navigate_to(repository, "Details")
    if appliance.version < "5.9":
        refresh = view.browser.refresh
    else:
        refresh = view.toolbar.refresh.click
    wait_for(
        lambda: view.entities.summary("Properties").get_text_of("Status") == "successful",
        timeout=60,
        fail_func=refresh
    )
    yield repository

    if repository.exists:
        repository.delete()


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

    if cat_item.exists:
        cat_item.delete()


@pytest.fixture(scope="module")
def ansible_catalog(appliance, ansible_catalog_item):
    catalog_ = appliance.collections.catalogs.create(fauxfactory.gen_alphanumeric(),
                                                     description="my ansible catalog",
                                                     items=[ansible_catalog_item.name])
    ansible_catalog_item.catalog = catalog_
    yield catalog_

    if catalog_.exists:
        catalog_.delete()
        ansible_catalog_item.catalog = None


@pytest.fixture(scope="module")
def ansible_service_catalog(appliance, ansible_catalog_item, ansible_catalog):
    service_catalog_ = ServiceCatalogs(appliance, ansible_catalog, ansible_catalog_item.name)
    return service_catalog_


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
        service_request.remove_request()
    yield cat_item_name
    service = MyService(appliance, cat_item_name)
    if service.exists:
        service.delete()
