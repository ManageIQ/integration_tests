# -*- coding: utf-8 -*-
import pytest

from cfme.control.explorer import PolicyProfile, VMCompliancePolicy
from cfme.infrastructure.virtual_machines import (assign_policy_profiles, get_first_vm_title,
    unassign_policy_profiles)
from utils.providers import setup_a_provider as _setup_a_provider


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider("infra")


@pytest.mark.meta(blockers=[1155284])
@pytest.mark.ignore_stream("5.2")
def test_scope_windows_registry_stuck(request, setup_a_provider):
    """If you provide Scope checking windows registry, it messes CFME up. Recoverable."""
    policy = VMCompliancePolicy(
        "Windows registry scope glitch testing Compliance Policy",
        active=True,
        scope=r"fill_registry(HKLM\SOFTWARE\Microsoft\CurrentVersion\Uninstall\test, "
        r"some value, INCLUDES, some content)"
    )
    request.addfinalizer(lambda: policy.delete() if policy.exists else None)
    policy.create()
    profile = PolicyProfile(
        "Windows registry scope glitch testing Compliance Policy",
        policies=[policy]
    )
    request.addfinalizer(lambda: profile.delete() if profile.exists else None)
    profile.create()
    # Now assign this malformed profile to a VM
    vm = get_first_vm_title()
    assign_policy_profiles(vm, profile.description, via_details=True)
    # It should be screwed here, but do additional check
    pytest.sel.force_navigate("dashboard")
    pytest.sel.force_navigate("infrastructure_virtual_machines")
    assert "except" not in pytest.sel.title().lower()
    unassign_policy_profiles(vm, profile.description, via_details=True)
