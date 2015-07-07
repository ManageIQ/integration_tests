# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.control.explorer import PolicyProfile, VMControlPolicy
from cfme.control.import_export import export_form


@pytest.fixture(scope="module")
def policy_profile(request):
    policy = VMControlPolicy(fauxfactory.gen_alpha())
    policy.create()
    request.addfinalizer(policy.delete)
    profile = PolicyProfile(fauxfactory.gen_alpha(), policies=[policy])
    profile.create()
    request.addfinalizer(profile.delete)
    return profile


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
    pytest.sel.force_navigate("control_import_export")
    pytest.sel.select(export_form.type, "Policy Profiles")
    try:
        export_form.available.select_by_visible_text(str(policy_profile.description))
    except pytest.sel.NoSuchElementException:
        pytest.fail("The policy profile to export was not displayed")
