from urllib.parse import urlparse

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainDetailsView
from cfme.base.credential import Credential
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.rest import assert_response


pytestmark = [
    test_requirements.automate,
    pytest.mark.meta(server_roles="+git_owner"),
]

GIT_REPO_URL = "https://github.com/RedHatQE/ManageIQ-automate-git.git"


@pytest.fixture
def imported_domain(appliance):
    repo = appliance.collections.automate_import_exports.instantiate(
        import_type="git", url=GIT_REPO_URL, verify_ssl=False
    )
    domain = repo.import_domain_from(branch="origin/master")
    yield domain
    domain.delete_if_exists()


@pytest.fixture(scope="module")
def new_user(appliance):
    """This fixture creates new user which assigned with non-super group"""
    group = appliance.collections.groups.instantiate(description='EvmGroup-administrator')
    user = appliance.collections.users.create(
        name="user_{}".format(fauxfactory.gen_alphanumeric().lower()),
        credential=Credential(principal='uid{}'.format(fauxfactory.gen_alphanumeric(4)),
                              secret='{password}'.format(password=fauxfactory.gen_alphanumeric(4))),
        email=fauxfactory.gen_email(),
        groups=[group],
        cost_center="Workload",
        value_assign="Database",
    )
    yield user
    user.delete_if_exists()


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[BZ(1714493)])
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
@pytest.mark.meta(automates=[BZ(1714493)])
def test_automate_git_domain_displayed_in_service(appliance):
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
    url = cfme_data.ansible_links.playbook_repositories.automate_domain
    repo = appliance.collections.automate_import_exports.instantiate(
        import_type="git", url=url, verify_ssl=True
    )
    imported_domain = repo.import_domain_from(branch="origin/master")
    collection = appliance.collections.catalog_items
    cat_item = collection.instantiate(collection.GENERIC, "test")
    view = navigate_to(cat_item, "Add")
    path = (
        "Datastore",
        "{0} ({1}) ({0}) (Locked)".format(imported_domain.name, "origin/master"),
        "Service",
        "Generic",
        "StateMachines",
        "GenericLifecycle",
        "provision"
    )
    view.provisioning_entry_point.fill(path, include_domain=True)
    assert view.provisioning_entry_point.value.split('/') == ['', imported_domain.name, *path[2:]]


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[BZ(1714493)])
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
    repo = appliance.collections.automate_import_exports.instantiate(
        import_type="git", url=url, verify_ssl=True
    )
    with pytest.raises(AssertionError,
                       match="Selected branch or tag contains more than one domain"):
        domain = repo.import_domain_from(branch="origin/master")
        request.addfinalizer(domain.delete_if_exists)
        assert not domain.exists


@pytest.mark.meta(automates=[BZ(1714493)])
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
    repo = appliance.collections.automate_import_exports.instantiate(
        import_type="git", url=url, verify_ssl=verify_ssl
    )
    domain = repo.import_domain_from(**{param_type: param_value})
    request.addfinalizer(domain.delete)
    assert domain.exists


@pytest.mark.manual
@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(coverage=[1677575])
def test_import_export_domain_with_ansible_method():
    """This test case tests support of Export/Import of Domain with Ansible Method

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.11
        casecomponent: Automate
        tags: automate
        setup:
            1. Start server_roles - 'git_owner'
        testSteps:
            1. Navigate to Automation > Automate > Import/Export
            2. Import/Export 'Domain' using ansible method
        expectedResults:
            1.
            2. Domain should get imported and seen in domain list

    Bugzilla:
        1677575
    """
    pass


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[BZ(1714493)])
def test_refresh_git_current_user(imported_domain, new_user):
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Automate
        tags: automate
        testSteps:
            1. created non-super user 'user1' along with default 'admin' user.
            2. Using admin user imported git repo.:
               'https://github.com/ramrexx/CloudForms_Essentials.git' or any other repo.
            3. Logged in with admin and refreshed domain- 'CloudForms_Essentials' or other domain.
               Then checked all tasks.
            4. Found user name 'admin' next to 'Refresh git repository'.
            5. Then checked instances in that domain by logging in with user 'user1' and 'admin'.
            6. Logged in with non-super user 'user1' and refreshed domain - 'CloudForms_Essentials'.
               Then checked all tasks.
            7. Found user name 'user1' next to 'Refresh git repository'.
            8. Then checked instances in that domain by logging in with user 'user1' and 'admin'.
        expectedResults:
            1.
            2.
            3.
            4.
            5. It shows that
               e.g. 'Automate Instance [Provisioning - Updated 2019-01-15 11:41:43 UTC by admin]'
            6.
            7.
            8. It shows that
               e.g. 'Automate Instance [Provisioning - Updated 2019-01-15 11:44:43 UTC by user1]'
               Hence, correct user that calls refresh automation domain from git branch is shown.
    Bugzilla:
        1592428
    """
    tasks_collection = imported_domain.appliance.collections.tasks

    # Refreshed imported domain by 'Admin' user
    imported_domain.refresh(branch_or_tag='Branch', git_branch='origin/master')
    view = imported_domain.create_view(DomainDetailsView)
    view.flash.assert_message("Successfully refreshed!")
    view = navigate_to(tasks_collection, 'AllTasks')

    # Collecting list of all tasks performed by users
    all_tasks = view.tabs.alltasks.table.read()
    for task in all_tasks:
        if task['Task Name'] == 'Refresh git repository':
            assert task['User'] == 'admin'
            break
    else:
        raise NameError("Task not found")

    with new_user:
        # Refreshed imported domain by non-super user
        imported_domain.refresh(branch_or_tag='Branch', git_branch='origin/master')
        view = navigate_to(tasks_collection, 'AllTasks')

        # Collecting list of all tasks performed by users
        all_tasks = view.tabs.alltasks.table.read()
        for task in all_tasks:
            if task['Task Name'] == 'Refresh git repository':
                assert task['User'] == new_user.credential.principal
                break
        else:
            raise NameError("Task not found")


@test_requirements.rest
@pytest.mark.tier(3)
@pytest.mark.ignore_stream("5.10")
def test_domain_import_git_rest(appliance, request):
    """
    This test checks importing datastore from git via REST

    Polarion:
        assignee: pvala
        initialEstimate: 1/15h
        startsin: 5.11
        casecomponent: Automate
        setup:
            1. Enable server role: Git Repositories Owner
        testSteps:
            1. Send a request POST /api/automate_domains
                Query: {
                    "action": "create_from_git",
                    "git_url": "https://github.com/RedHatQE/ManageIQ-automate-git",
                    "ref_type": "branch",
                    "ref_name": "master"
                }
        expectedResults:
            1. The automate domain must have been created successfully.

    Bugzilla:
        1600961
    """
    collection = appliance.rest_api.collections.automate_domains
    data = {
        "git_url": GIT_REPO_URL,
        "ref_type": "branch",
        "ref_name": "origin/master"
    }
    collection.action.create_from_git(**data)
    assert_response(appliance)

    automate_domain = collection.get(name="testdomain")

    @request.addfinalizer
    def _cleanup():
        # cannot delete a locked domain via REST, so doing it via UI
        domain = appliance.collections.domains.instantiate(name="testdomain")
        domain.delete_if_exists()

    assert automate_domain.exists


@pytest.mark.tier(1)
def test_automate_git_import_case_insensitive(request, appliance):
    """
    bin/rake evm:automate:import PREVIEW=false
    GIT_URL=https://github.com/RedHatQE/ManageIQ-automate-git REF=TestBranch
    This should not cause an error (the actual name of the branch is
    TestBranch).

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/8h
        tags: automate
        startsin: 5.7
    """
    appliance.ssh_client.run_rake_command(
        "evm:automate:import PREVIEW=false "
        "GIT_URL=https://github.com/RedHatQE/ManageIQ-automate-git REF=TestBranch"
    )
    domain = appliance.collections.domains.instantiate(name="testdomain")
    request.addfinalizer(domain.delete_if_exists)
    assert domain.exists
