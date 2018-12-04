import pytest
from six.moves.urllib.parse import urlparse

from cfme.automate.import_export import AutomateGitRepository
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.meta(server_roles="+git_owner"),
]

GIT_REPO_URL = "https://github.com/RedHatQE/ManageIQ-automate-git.git"


@pytest.fixture
def branch(appliance):
    if appliance.version < "5.9":
        return "origin/5.8"
    else:
        return "origin/master"


@pytest.fixture
def imported_domain(appliance, branch):
    repo = AutomateGitRepository(
        url=GIT_REPO_URL,
        verify_ssl=False,
        appliance=appliance
    )
    domain = repo.import_domain_from(branch=branch)
    yield domain
    domain.delete_if_exists()


@pytest.mark.tier(1)
def test_automate_git_domain_removed_from_disk(appliance, imported_domain):
    """
    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
    """
    imported_domain.delete()
    repo_path = urlparse(GIT_REPO_URL).path
    assert appliance.ssh_client.run_command(
        '[ ! -d "/var/www/vmdb/data/git_repos{}" ]'.format(repo_path)).success


@pytest.mark.tier(2)
def test_automate_git_domain_displayed_in_service(appliance, imported_domain, branch):
    """Tests if a domain is displayed in a service.

    Checks if the domain imported from git is displayed and usable in the pop-up tree in the
    dialog for creating services.


    Polarion:
        assignee: dmisharo
        casecomponent: automate
        initialEstimate: 1/20h
    """
    collection = appliance.collections.catalog_items
    cat_item = collection.instantiate(collection.GENERIC, "test")
    view = navigate_to(cat_item, "Add")
    view.field_entry_point.fill("")
    view.modal.tree.click_path(
        "Datastore",
        "{0} ({1}) ({0}) (Locked)".format(imported_domain.name, branch),
        "Service",
        "Provisioning",
        "StateMachines",
        "ServiceProvision_Template",
        "CatalogItemInitialization"
    )
    view.modal.include_domain.fill(True)
    view.modal.apply.click()
    assert view.field_entry_point.value == ("/{}/Service/Provisioning/StateMachines/"
        "ServiceProvision_Template/CatalogItemInitialization".format(imported_domain.name))
