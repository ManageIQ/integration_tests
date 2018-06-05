import pytest
from six.moves.urllib.parse import urlparse

from cfme.automate.import_export import AutomateGitRepository


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


def test_automate_git_domain_removed_from_disk(appliance, imported_domain):
    imported_domain.delete()
    repo_path = urlparse(GIT_REPO_URL).path
    assert appliance.ssh_client.run_command(
        '[ ! -d "/var/www/vmdb/data/git_repos{}" ]'.format(repo_path)).success
