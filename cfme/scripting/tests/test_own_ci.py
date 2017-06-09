from __future__ import print_function
import pytest
from utils import path
from commands import getoutput
from .. import ci
from click.testing import CliRunner

TEST_BRANCH_NAME = 'miq-test-branch'
PULL_REQUEST = 1337


@pytest.fixture
def fake_repo(request, tmpdir):
    repo = tmpdir / 'repo'
    ci.do(['git', 'clone', path.project_path, repo, '--bare'])
    if request.node.get_marker('create_history'):
        branch_wd = tmpdir / 'branch-for-wd'
        ci.do(['git', 'clone', repo, branch_wd])
        with branch_wd.as_cwd():
            ci.do(['git', 'checkout', '-b', TEST_BRANCH_NAME])
            file = branch_wd.join('setup.py')
            file.write_binary(file.read_binary() + b'\n# extra')
            ci.do(['git', 'commit', '-a', '-m', 'test commit'])
            ci.do(['git', 'push', 'origin', TEST_BRANCH_NAME])

            ci.do(['git', 'push', 'origin',
                   '{}:refs/pull/{}/head'.format(TEST_BRANCH_NAME, PULL_REQUEST),
                   ])
    return repo


@pytest.fixture
def ci_checkout(request, monkeypatch, fake_repo, tmpdir):

    co = tmpdir.join('checkout')
    ci.do(['git', 'clone', fake_repo, co])
    ci.do([
        'git', 'clone',
        ci.qe_yaml_path(path.project_path),
        ci.qe_yaml_path(co),
    ])

    # todo: undo the need ofr this evil
    monkeypatch.setattr(path, 'original_project_path',
                        path.project_path, raising=False)
    monkeypatch.setattr(path, 'project_path', co)
    if request.node.get_marker('chdir'):
        monkeypatch.chdir(co)
    return co


@pytest.fixture
def _runner():
    return CliRunner()


@pytest.fixture
def invoke(_runner):

    def invoke(*k, **kw):
        result = _runner.invoke(
            *k, **kw)
        print(result.output_bytes)
        return result
    return invoke


@pytest.mark.chdir
def test_ci_fetch_credentials(ci_checkout, invoke):
    invoke(ci.fetch_credentials)


@pytest.mark.chdir
def test_fetch_credentials_fails_when_missing(ci_checkout, invoke):
    ci.qe_yaml_path(ci_checkout).remove()
    result = invoke(ci.fetch_credentials)
    assert isinstance(result.exception, SystemExit)


@pytest.mark.chdir
def test_fetch_credentials_clone_when_given(ci_checkout, invoke):
    ci.qe_yaml_path(ci_checkout).remove()
    result = invoke(ci.fetch_credentials, [
        '--credentials-repo', path.original_project_path.strpath])
    assert result.exception is None
    assert ci.qe_yaml_path(ci_checkout).isdir()


@pytest.mark.parametrize('commit, verified', [
    ("b08d0396d798626ce3f07050cfc5c0cd2a54ce28", True),
    ("39dbccaafe392d1a75900055c24088c2cafca8e0", False),
])
def test_verify_commit(invoke, commit, verified):
    result = invoke(ci.verify_commit, [commit])
    if verified:
        print(result.exception)
        assert result.exception is None
    else:
        assert isinstance(result.exception, SystemExit)


@pytest.mark.chdir
def test_prepare_workdir_checkout_needs_repo(invoke):
    result = invoke(ci.prepare_workdir_checkout)
    assert b'--cfme-repo' in result.output_bytes
    assert result.exception


@pytest.mark.chdir
def test_prepare_workdir_checkout_needs_work(invoke, ci_checkout):
    result = invoke(ci.prepare_workdir_checkout, [
        '--cfme-repo', str(ci_checkout)
    ])
    assert b'branch or pr needed' in result.output_bytes
    assert result.exception


@pytest.mark.chdir
@pytest.mark.create_history
def test_prepare_workdir_for_branch_prepares_branch(invoke, ci_checkout, fake_repo):
    result = invoke(ci.prepare_workdir_checkout, [
        '--cfme-repo', str(fake_repo),
        '--branch', TEST_BRANCH_NAME,
    ])
    assert result.exception is None
    assert ('* ' + TEST_BRANCH_NAME) in getoutput("git branch")


@pytest.mark.chdir
@pytest.mark.create_history
def test_prepare_workdir_for_pr_prepares_branch(invoke, ci_checkout, fake_repo):
    result = invoke(ci.prepare_workdir_checkout, [
        '--cfme-repo', str(fake_repo),
        '--cfme-pr', PULL_REQUEST,
        '--no-verify',
    ])
    assert result.exception is None
    assert '* pr-{}'.format(PULL_REQUEST) in getoutput("git branch")


@pytest.mark.chdir
def test_prepare_configfiles(invoke, ci_checkout, monkeypatch):
    conf_path = ci_checkout.join('conf')
    monkeypatch.setattr(path, "conf_path", conf_path)
    result = invoke(ci.prepare_workdir_configfiles, [
        '--appliance', 'https://example.com',
    ])
    assert not result.exception

    assert conf_path.join("env.local.yaml").isfile()
