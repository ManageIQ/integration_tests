# -*- coding: utf-8 -*-

import pytest

from conftest import (
    generate_update_tests, download_repo_files, run_cfme_updates, run_platform_updates,
    enable_repos, rh_updates_data
)


def pytest_generate_tests(metafunc):
    generate_update_tests(metafunc, 'cli')


try:
    skip_cli_direct = not rh_updates_data()['cli']['test_direct']
except KeyError:
    skip_cli_direct = True


@pytest.mark.uncollectif(skip_cli_direct,
    reason='RH Update test using CLI (over SSH) is not enabled')
@pytest.mark.long_running
@pytest.mark.ignore_stream("upstream")
@pytest.mark.rh_updates
def test_cli_direct(appliance_set, rh_updates_data, soft_assert):
    target_appliances = appliance_set.all_appliance_names

    download_repo_files(appliance_set, rh_updates_data, 'cli', target_appliances)
    enable_repos(appliance_set, rh_updates_data, 'cli', target_appliances)

    run_cfme_updates(appliance_set, rh_updates_data, soft_assert, cli_only=True)
    run_platform_updates(appliance_set, cli_only=True)
