# -*- coding: utf-8 -*-
import fauxfactory
import json
import pytest

from cfme import test_requirements
from cfme.services.catalogs.ansible_catalog_item import AnsiblePlaybookCatalogItem
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogBundle
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.myservice import MyService
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(server_roles=["+embedded_ansible"]),
    pytest.mark.ignore_stream("upstream", '5.7'),
    test_requirements.ansible
]


SERVICE_CATALOG_VALUES = [
    ("default", None, "localhost"),
    ("blank", "", "localhost"),
    ("unavailable_host", "unavailable_host", "unavailable_host")
]


@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.wait_for_embedded_ansible()


@pytest.yield_fixture(scope="module")
def ansible_repository(appliance, wait_for_ansible):
    repositories = appliance.collections.ansible_repositories
    repository = repositories.create(
        name=fauxfactory.gen_alpha(),
        url="https://github.com/quarckster/ansible_playbooks",
        description=fauxfactory.gen_alpha())
    yield repository

    if repository.exists:
        repository.delete()


@pytest.yield_fixture(scope="module")
def ansible_credential(appliance):
    credential = appliance.collections.ansible_credentials.create(
        fauxfactory.gen_alpha(),
        "Machine",
        username=fauxfactory.gen_alpha(),
        password=fauxfactory.gen_alpha()
    )
    yield credential

    if credential.exists:
        credential.delete()


@pytest.yield_fixture(scope="module")
def ansible_catalog_item(ansible_repository):
    cat_item = AnsiblePlaybookCatalogItem(
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
    cat_item.create()
    yield cat_item

    if cat_item.exists:
        cat_item.delete()


@pytest.yield_fixture(scope="module")
def catalog(ansible_catalog_item):
    catalog_ = Catalog(fauxfactory.gen_alphanumeric(), items=[ansible_catalog_item.name])
    catalog_.create()
    ansible_catalog_item.catalog = catalog_
    yield catalog_

    if catalog_.exists:
        catalog_.delete()
        ansible_catalog_item.catalog = None


@pytest.fixture(scope="module")
def service_catalog(appliance, ansible_catalog_item, catalog):
    service_catalog_ = ServiceCatalogs(appliance, catalog, ansible_catalog_item.name)
    return service_catalog_


@pytest.yield_fixture
def service_request(appliance, ansible_catalog_item):
    request_descr = "Provisioning Service [{0}] from [{0}]".format(ansible_catalog_item.name)
    service_request_ = appliance.collections.requests.instantiate(description=request_descr)
    yield service_request_

    if service_request_.exists:
        service_request_.remove_request()


@pytest.yield_fixture
def service(appliance, ansible_catalog_item):
    service_ = MyService(appliance, ansible_catalog_item.name)
    yield service_

    if service_.exists:
        service_.delete()


@pytest.mark.tier(1)
def test_service_ansible_playbook_available():
    view = navigate_to(AnsiblePlaybookCatalogItem("", "", provisioning={}), "PickItemType")
    assert "Ansible Playbook" in [option.text for option in view.catalog_item_type.all_options]


@pytest.mark.tier(1)
def test_service_ansible_playbook_crud(ansible_repository):
    cat_item = AnsiblePlaybookCatalogItem(
        fauxfactory.gen_alphanumeric(),
        fauxfactory.gen_alphanumeric(),
        provisioning={
            "repository": ansible_repository.name,
            "playbook": "dump_all_variables.yml",
            "machine_credential": "CFME Default Credential",
            "create_new": True,
            "provisioning_dialog_name": fauxfactory.gen_alphanumeric()
        }
    )
    cat_item.create()
    assert cat_item.exists
    with update(cat_item):
        new_name = "edited_{}".format(fauxfactory.gen_alphanumeric())
        cat_item.name = new_name
        cat_item.provisioning = {
            "playbook": "copy_file_example.yml"
        }
    view = navigate_to(cat_item, "Details")
    assert new_name in view.entities.title.text
    assert view.entities.provisioning.info.get_text_of("Playbook") == "copy_file_example.yml"
    cat_item.delete()
    assert not cat_item.exists


def test_service_ansible_playbook_tagging(ansible_catalog_item):
    """ Tests ansible_playbook tag addition, check added tag and removal

    Steps:
        1. Login as a admin
        2. Add tag for ansible_playbook
        3. Check added tag
        4. Remove the given tag
    """
    ansible_catalog_item.add_tag('Department', 'Support')
    assert any(tag.category.display_name == "Department" and tag.display_name == "Support"
               for tag in ansible_catalog_item.get_tags()), (
        'Assigned tag was not found on the details page')
    ansible_catalog_item.remove_tag('Department', 'Support')
    assert ansible_catalog_item.get_tags() == []


@pytest.mark.tier(2)
def test_service_ansible_playbook_negative():
    view = navigate_to(AnsiblePlaybookCatalogItem("", "", {}), "Add")
    view.fill({
        "name": fauxfactory.gen_alphanumeric(),
        "description": fauxfactory.gen_alphanumeric()
    })
    assert not view.add.active


@pytest.mark.tier(2)
def test_service_ansible_playbook_bundle(ansible_catalog_item):
    """Ansible playbooks are not designed to be part of a cloudforms service bundle."""
    view = navigate_to(CatalogBundle(), "BundleAdd")
    options = view.resources.select_resource.all_options
    assert ansible_catalog_item.name not in [o.text for o in options]


@pytest.mark.tier(2)
def test_service_ansible_playbook_provision_in_requests(appliance, ansible_catalog_item,
                                                        service_catalog):
    """Tests if ansible playbook service provisioning is shown in service requests."""
    service_catalog.order()
    cat_item_name = ansible_catalog_item.name
    request_descr = "Provisioning Service [{0}] from [{0}]".format(cat_item_name)
    service_request = appliance.collections.requests.instantiate(description=request_descr)
    assert service_request.exists()


@pytest.mark.tier(2)
def test_service_ansible_playbook_confirm():
    """Tests after selecting playbook additional widgets appear and are pre-populated where
    possible.
    """
    view = navigate_to(AnsiblePlaybookCatalogItem, "Add")
    assert view.provisioning.is_displayed
    assert view.retirement.is_displayed
    assert view.provisioning.repository.is_displayed
    assert view.provisioning.hosts.is_displayed
    assert view.provisioning.verbosity.is_displayed
    assert view.retirement.repository.is_displayed
    assert view.retirement.hosts.is_displayed
    assert view.retirement.verbosity.is_displayed
    assert view.retirement.remove_resources.is_displayed
    assert view.provisioning.hosts.value == "localhost"
    assert view.retirement.hosts.value == "localhost"
    assert view.retirement.verbosity.selected_option == "0 (Normal)"
    assert view.retirement.remove_resources.selected_option == "Yes"


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda host_type, action:
                         host_type == "blank" and action == "retirement")
@pytest.mark.parametrize("host_type,order_value,result", SERVICE_CATALOG_VALUES, ids=[
    value[0] for value in SERVICE_CATALOG_VALUES])
@pytest.mark.parametrize("action", ["provisioning", "retirement"])
def test_service_ansible_playbook_order_retire(appliance, ansible_catalog_item, service_catalog,
        service_request, service, host_type, order_value, result, action):
    """Test ordering and retiring ansible playbook service against default host, blank field and
    unavailable host.
    """
    service_catalog.ansible_dialog_values = {"hosts": order_value}
    service_catalog.order()
    service_request.wait_for_request()
    if action == "retirement":
        service.retire()
    view = navigate_to(service, "Details")
    assert result == view.provisioning.details.get_text_of("Hosts")


def test_service_ansible_playbook_plays_table(ansible_catalog_item, service_catalog,
        service_request, service, soft_assert):
    """Plays table in provisioned and retired service should contain at least one row."""
    service_catalog.order()
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    soft_assert(len(view.provisioning.plays.fields) > 1, "Plays table in provisioning tab is empty")
    service.retire()
    soft_assert(len(view.retirement.plays.fields) > 1, "Plays table in retirement tab is empty")


@pytest.mark.tier(3)
def test_service_ansible_playbook_order_credentials(ansible_catalog_item, ansible_credential,
        service_catalog):
    """Test if credentials avaialable in the dropdown in ordering ansible playbook service
    screen.
    """
    with update(ansible_catalog_item):
        ansible_catalog_item.provisioning = {
            "machine_credential": ansible_credential.name
        }
    view = navigate_to(service_catalog, "Order")
    options = [o.text for o in view.machine_credential.all_options]
    assert ["<Default>", "CFME Default Credential", ansible_credential.name] == options


@pytest.mark.tier(3)
@pytest.mark.parametrize("action", ["provisioning", "retirement"])
def test_service_ansible_playbook_pass_extra_vars(service_catalog, service_request, service,
        action):
    """Test if extra vars passed into ansible during ansible playbook service provision and
    retirement."""
    service_catalog.order()
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    if action == "retirement":
        service.retire()
    pre = getattr(view, action).standart_output.text
    json_str = pre.split("--------------------------------")
    result_dict = json.loads(json_str[5].replace('", "', "").replace('\\"', '"').replace(
        '\\, "', '",').split('" ] } PLAY')[0])
    assert result_dict["some_var"] == "some_value"


@pytest.mark.tier(3)
def test_service_ansible_execution_ttl(request, service_catalog, ansible_catalog_item, service,
         service_request):
    """Test if long running processes allowed to finish. There is a code that guarantees to have 100
    retries with a minimum of 1 minute per retry. So we need to run ansible playbook service more
    than 100 minutes and set max ttl greater than ansible playbook running time.
    """
    with update(ansible_catalog_item):
        ansible_catalog_item.provisioning = {
            "playbook": "long_running_playbook.yml",
            "max_ttl": 200
        }

    def _revert():
        with update(ansible_catalog_item):
            ansible_catalog_item.provisioning = {
                "playbook": "dump_all_variables.yml",
                "max_ttl": ""
            }

    request.addfinalizer(_revert)
    service_catalog.order()
    service_request.wait_for_request(method="ui", num_sec=200 * 60, delay=120)
    view = navigate_to(service, "Details")
    assert view.provisioning.results.get_text_of("Status") == "successful"
