import pytest

from cfme.fixtures.pytest_store import store


def pytest_addoption(parser):
    group = parser.getgroup('Upstream testing')
    group.addoption('--dev-repo',
                    action='store',
                    default=None,
                    dest='dev_repo',
                    help='Specify to use the IPAppliance.use_dev_branch()')
    group.addoption('--dev-branch',
                    action='store',
                    default='master',
                    dest='dev_branch',
                    help='Specify the branch of the remote repo.')


def pytest_sessionstart(session):
    if store.parallelizer_role == 'master':
        return
    if session.config.getoption("dev_repo") is None:
        return
    if store.current_appliance.is_downstream:
        store.write_line("Cannot git update downstream appliances ...")
        pytest.exit('Failed to git update this appliance, because it is downstream')
    dev_repo = session.config.getoption("dev_repo")
    dev_branch = session.config.getoption("dev_branch")
    store.write_line(
        "Changing the upstream appliance {} to {}#{} ...".format(
            store.current_appliance.hostname, dev_repo, dev_branch))
    store.current_appliance.use_dev_branch(dev_repo, dev_branch)
    store.write_line("Appliance change finished ...")
