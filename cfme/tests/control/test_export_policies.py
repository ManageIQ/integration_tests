# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.control.explorer.policies import VMControlPolicy
from cfme.control.explorer.policy_profiles import PolicyProfile
from cfme.control.import_export import is_imported
from cfme import test_requirements


@pytest.fixture(scope="module")
def policy_profile(request):
    policy = VMControlPolicy(fauxfactory.gen_alpha())
    policy.create()
    request.addfinalizer(policy.delete)
    profile = PolicyProfile(fauxfactory.gen_alpha(), policies=[policy])
    profile.create()
    request.addfinalizer(profile.delete)
    return profile


@test_requirements.control
@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1202229], automates=[1202229])
def test_policy_profiles_listed(policy_profile):
    """This test verifies that policy profiles are displayed in the selector for export.

    Prerequisities:
        * A Policy Profile

    Steps:
        * Go to the Control / Import/Export page
        * Select ``Policy Profiles`` from the ``Export:`` dropdown.
        * Assert that the policy profile is displayed in the selector.
    """
    is_imported(policy_profile)
