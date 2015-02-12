# -*- coding: utf-8 -*-

import pytest

from conftest import (
    generate_update_tests, update_registration, register_appliances, download_repo_files,
    run_cfme_updates, run_platform_updates, enable_repos, add_channels, rh_updates_data
)


def pytest_generate_tests(metafunc):
    generate_update_tests(metafunc, 'sat5')

try:
    skip_sat5_direct = not rh_updates_data()['sat5']['test_direct']
except KeyError:
    skip_sat5_direct = True


@pytest.mark.uncollectif(skip_sat5_direct,
    reason='RH Update test using Sat5 is not enabled')
@pytest.mark.long_running
@pytest.mark.ignore_stream("upstream")
@pytest.mark.rh_updates
def test_sat5_direct(appliance_set, rh_updates_data, soft_assert):
    target_appliances = appliance_set.all_appliance_names

    update_registration(appliance_set, rh_updates_data, 'sat5')
    register_appliances(appliance_set, target_appliances, soft_assert)

    download_repo_files(appliance_set, rh_updates_data, 'sat5', target_appliances)
    enable_repos(appliance_set, rh_updates_data, 'sat5', target_appliances)
    add_channels(appliance_set, rh_updates_data, target_appliances)

    # In 5.3.1 and above, platform updates are a part of cfme update process on non-DB appliances
    run_cfme_updates(appliance_set, rh_updates_data, soft_assert)
    if appliance_set.primary.version < '5.3.1':
        run_platform_updates(appliance_set)
