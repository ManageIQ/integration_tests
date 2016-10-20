# -*- coding: utf-8 -*-
import pytest


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
    if pytest.store.parallelizer_role == 'master':
        return
    if session.config.getoption("dev_repo") is None:
        return
    if pytest.store.current_appliance.is_downstream:
        pytest.store.write_line("Cannot git update downstream appliances ...")
        pytest.exit('Failed to git update this appliance, because it is downstream')
    dev_repo = session.config.getoption("dev_repo")
    dev_branch = session.config.getoption("dev_branch")
    pytest.store.write_line(
        "Changing the upstream appliance {} to {}#{} ...".format(
            pytest.store.current_appliance.address, dev_repo, dev_branch))
    pytest.store.current_appliance.use_dev_branch(dev_repo, dev_branch)
    pytest.store.write_line("Appliance change finished ...")
