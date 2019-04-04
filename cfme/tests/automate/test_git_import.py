import pytest
from six.moves.urllib.parse import urlparse

from cfme.automate.import_export import AutomateGitRepository
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.meta(server_roles="+git_owner"),
]

GIT_REPO_URL = "https://github.com/RedHatQE/ManageIQ-automate-git.git"


@pytest.fixture
def imported_domain(appliance):
    repo = AutomateGitRepository(
        url=GIT_REPO_URL,
        verify_ssl=False,
        appliance=appliance
    )
    domain = repo.import_domain_from(branch="origin/master")
    yield domain
    domain.delete_if_exists()


@pytest.mark.tier(1)
def test_automate_git_domain_removed_from_disk(appliance, imported_domain):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/8h
        tags: automate
    """
    imported_domain.delete()
    repo_path = urlparse(GIT_REPO_URL).path
    assert appliance.ssh_client.run_command(
        '[ ! -d "/var/www/vmdb/data/git_repos{}" ]'.format(repo_path)).success


@pytest.mark.tier(2)
def test_automate_git_domain_displayed_in_service(appliance, imported_domain):
    """Tests if a domain is displayed in a service.
       Checks if the domain imported from git is displayed and usable in the pop-up tree in the
       dialog for creating services.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/20h
        tags: automate
    """
    collection = appliance.collections.catalog_items
    cat_item = collection.instantiate(collection.GENERIC, "test")
    view = navigate_to(cat_item, "Add")
    view.provisioning_entry_point.click()
    view.modal.tree.click_path(
        "Datastore",
        "{0} ({1}) ({0}) (Locked)".format(imported_domain.name, "origin/master"),
        "Service",
        "Provisioning",
        "StateMachines",
        "ServiceProvision_Template",
        "CatalogItemInitialization"
    )
    view.modal.include_domain.fill(True)
    view.modal.apply.click()
    assert view.provisioning_entry_point.value == ("/{}/Service/Provisioning/StateMachines/"
        "ServiceProvision_Template/CatalogItemInitialization".format(imported_domain.name))


@pytest.mark.tier(3)
def test_automate_git_import_multiple_domains(request, appliance):
    """
    Importing of multiple domains from a single git repository is not allowed.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/12h
        caseimportance: medium
        caseposneg: negative
        testtype: functional
        startsin: 5.10
        casecomponent: Automate
        tags: automate
        title: Test automate git import multiple domains
        testSteps:
            1. Enable server role: git Repositories Owner
            2. Navigate to Automation > Automate > Import/Export
            3. Import multiple domains from a single git repository
        expectedResults:
            1.
            2.
            3. Import of multiple domains from a single git repo is not allowed
    """
    url = "https://github.com/ganeshhubale/ManageIQ-automate-git"
    repo = AutomateGitRepository(url=url, verify_ssl=True, appliance=appliance)
    with pytest.raises(ValueError):
        domain = repo.import_domain_from(branch="origin/master")
        request.addfinalizer(domain.delete_if_exists)
        assert not domain.exists
