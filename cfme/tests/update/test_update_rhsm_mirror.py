# -*- coding: utf-8 -*-

import pytest

from conftest import (
    generate_update_tests, update_registration, register_appliances, download_repo_files,
    run_cfme_updates, enable_repos, rhn_mirror_setup, rh_updates_data
)


def pytest_generate_tests(metafunc):
    generate_update_tests(metafunc, 'rhsm')

try:
    skip_rhsm_rhn_mirror = not rh_updates_data()['rhsm']['test_rhn_mirror']
except KeyError:
    skip_rhsm_rhn_mirror = True


@pytest.mark.uncollectif(skip_rhsm_rhn_mirror,
    reason='RH Update test using RHSM/RHN Mirror is not enabled')
@pytest.mark.long_running
@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(blockers=["BZ#1160456"])
@pytest.mark.rh_updates
def test_rhsm_rhn_mirror(appliance_set, rh_updates_data, soft_assert):
    # Use only primary to register_appliances(), download_repo_files() and enable_repos()
    update_registration(appliance_set, rh_updates_data, 'rhsm')
    register_appliances(appliance_set, [appliance_set.primary.name], soft_assert)

    download_repo_files(appliance_set, rh_updates_data, 'rhsm', [appliance_set.primary.name])
    enable_repos(appliance_set, rh_updates_data, 'rhsm', [appliance_set.primary.name])
    rhn_mirror_setup(appliance_set, soft_assert)

    # In 5.3.1 and above, platform updates are a part of cfme update process on non-DB appliances
    # but RHN Mirror only downloads the CFME-related packages
    run_cfme_updates(appliance_set, rh_updates_data, soft_assert)
