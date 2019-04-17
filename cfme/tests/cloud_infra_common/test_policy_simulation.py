# -*- coding: utf-8 -*-
"""This module tests events that are invoked by Cloud/Infra VMs."""
import pytest

from cfme.cloud.provider import CloudProvider
from cfme.common.vm_views import PolicySimulationDetailsView
from cfme.common.vm_views import PolicySimulationView
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE_PER_CATEGORY
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2),
    pytest.mark.provider(
        classes=[CloudProvider, InfraProvider],
        selector=ONE_PER_CATEGORY,
        scope="module"
    ),
]


@pytest.mark.parametrize("navigation", ["provider_vms", "all_vms", "vm_summary"])
@pytest.mark.uncollectif(
    lambda navigation: navigation == "provider_vms" and (BZ(1686617).blocks or BZ(1686619).blocks),
    reason="This test is blocked by the following BZs: {}, {}".format(
        BZ(1686617).bug_id,
        BZ(1686619).bug_id
    )
)
def test_policy_simulation_ui(appliance, provider, navigation):
    """
    Bugzilla:
        1670456
        1686617
        1686619
        1688359
        1550503

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/6hr
    """
    # get a vm
    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.all()[0]
    my_filter = {"name": vm.name}

    # additional filter args for navigation via provider_vms and vm_summary
    if navigation != "all_vms":
        my_filter["provider"] = provider

    # create the filtered collection
    filtered_collection = collection.filter(my_filter)

    # navigate using filtered_collection if not using the vm's summary page
    if navigation != "vm_summary":
        view = navigate_to(filtered_collection, "PolicySimulation")
    # otherwise use the vm
    else:
        view = navigate_to(vm, "PolicySimulation", force=True)

    # check the quadicon
    assert view.form.entities.check_context_against_entities([vm])

    assert view.form.cancel_button.is_displayed
    view.form.policy_profile.select_by_visible_text("OpenSCAP profile")
    # now check that we can navigate to the right page
    if vm.provider.one_of(InfraProvider) or not BZ(1688359).blocks:
        view.form.entities.get_entity(name=vm.name).click()
        view = vm.create_view(PolicySimulationDetailsView, wait="10s")
        # check that the back button works
        view.back_button.click()
    # check that the cancel button works
    if not BZ(1670456).blocks:
        view = vm.create_view(PolicySimulationView, wait="10s")
        view.form.cancel_button.click()
        assert not view.is_displayed
