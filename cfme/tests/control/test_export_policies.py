import fauxfactory
import pytest

from cfme import test_requirements
from cfme.control.explorer.policies import VMControlPolicy
from cfme.control.import_export import is_imported


@pytest.fixture(scope="module")
def policy_profile_collection(appliance):
    return appliance.collections.policy_profiles


@pytest.fixture(scope="module")
def policy_collection(appliance):
    return appliance.collections.policies


@pytest.fixture(scope="module")
def policy_profile(request, policy_collection, policy_profile_collection):
    policy = policy_collection.create(VMControlPolicy, fauxfactory.gen_alpha())
    request.addfinalizer(policy.delete)
    profile = policy_profile_collection.create(fauxfactory.gen_alpha(), policies=[policy])
    request.addfinalizer(profile.delete)
    return profile


@test_requirements.control
@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1202229], automates=[1202229])
def test_policy_profiles_listed(appliance, policy_profile):
    """This test verifies that policy profiles are displayed in the selector for export.

    Prerequisities:
        * A Policy Profile

    Steps:
        * Go to the Control / Import/Export page
        * Select ``Policy Profiles`` from the ``Export:`` dropdown.
        * Assert that the policy profile is displayed in the selector.

    Polarion:
        assignee: dgaikwad
        casecomponent: Control
        caseimportance: low
        initialEstimate: 1/12h
    """
    is_imported(appliance, policy_profile)
