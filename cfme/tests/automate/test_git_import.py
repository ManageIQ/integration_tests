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
def test_automate_git_domain_displayed_in_service(appliance, imported_domain, branch):
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
        "{0} ({1}) ({0}) (Locked)".format(imported_domain.name, branch),
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


@pytest.mark.tier(2)
@pytest.mark.parametrize(
    ("url", "param_type", "param_value", "verify_ssl"),
    [
        (
            'https://github.com/ramrexx/CloudForms_Essentials.git',
            'branch',
            'origin/cf4.1',
            True
        ),
        (
            'https://github.com/RedHatQE/ManageIQ-automate-git.git',
            'tag',
            '0.1',
            False
        ),
        (
            "https://github.com/RedHatQE/ManageIQ-automate-git.git",
            "branch",
            "origin/master",
            False,
        ),
        (
            "https://github.com/ganeshhubale/ManageIQ-automate-git.git",
            "branch",
            "origin/test",
            False,
        ),
    ],
    ids=["with_branch", "with_tag", "with_top_level_domain", "without_top_level_domain"],
)
def test_domain_import_git(
    request, appliance, url, param_type, param_value, verify_ssl
):
    """This test case Verifies that a domain can be imported from git and Importing domain from git
       should work with or without the top level domain directory.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/6h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.7
        casecomponent: Automate
        tags: automate
        title: Test automate git domain import top level directory
        testSteps:
            1. Enable server role: git Repositories Owner
            2. Navigate to Automation > Automate > Import/Export
            3. Create a Git Repository with the contents of a domain directory without including
               the domain directory.
        expectedResults:
            1.
            2.
            3. Import should work with or without the top level domain directory.

    Bugzilla:
        1389823
    """
    repo = AutomateGitRepository(url=url, verify_ssl=verify_ssl, appliance=appliance)
    domain = repo.import_domain_from(**{param_type: param_value})
    request.addfinalizer(domain.delete)
    assert domain.exists
