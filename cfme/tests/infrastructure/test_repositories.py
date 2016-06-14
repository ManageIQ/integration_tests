import pytest

from cfme.infrastructure import repositories
from utils.update import update
from utils.wait import TimedOutError, wait_for


@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[1188427])
def test_repository_crud(soft_assert, random_string, request):
    repo_name = 'Test Repo {}'.format(random_string)
    repo = repositories.Repository(repo_name, '//testhost/share/path')
    request.addfinalizer(repo.delete)

    # create
    repo.create()

    # read
    assert repo.exists

    # update
    with update(repo):
        repo.name = 'Updated {}'.format(repo_name)

    with soft_assert.catch_assert():
        assert repo.exists, 'Repository rename failed'

        # Only change the name back if renaming succeeded
        with update(repo):
            repo.name = repo_name

    # delete
    repo.delete()
    try:
        wait_for(lambda: not repo.exists)
    except TimedOutError:
        raise AssertionError('failed to delete repository')
