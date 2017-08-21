import fauxfactory
import pytest

from cfme import test_requirements
from cfme.ansible.repositories import RepositoryCollection
from cfme.services.catalogs.ansible_catalog_item import AnsiblePlaybookCatalogItem
from utils.appliance.implementations.ui import navigate_to
from utils.update import update
from utils.version import current_version


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(server_roles=["+embedded_ansible"]),
    pytest.mark.uncollectif(lambda: current_version() < "5.8"),
    pytest.mark.ignore_stream("upstream"),
    test_requirements.ansible
]


@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.wait_for_embedded_ansible()


@pytest.yield_fixture(scope="module")
def ansible_repository(wait_for_ansible):
    repositories = RepositoryCollection()
    repository = repositories.create(
        fauxfactory.gen_alpha(),
        "https://github.com/quarckster/ansible_playbooks",
        description=fauxfactory.gen_alpha()
    )
    yield repository
    repository.delete()


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
    assert new_name in view.title.text
    assert view.provisioning.info.get_text_of("Playbook") == "copy_file_example.yml"
    cat_item.delete()
    assert not cat_item.exists
