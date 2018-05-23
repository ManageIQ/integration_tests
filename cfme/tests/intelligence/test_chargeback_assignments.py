# -*- coding: utf-8 -*-
import cfme.intelligence.chargeback.assignments as cb
import pytest
import random

from cfme.intelligence.chargeback.assignments import AssignmentsView
from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.chargeback
]


@pytest.mark.meta(blockers=[1273654])
def test_assign_compute_enterprise(appliance, virtualcenter_provider):
    """
    Polarion:
        assignee: nachandr
        casecomponent: candu
        caseimportance: low
        initialEstimate: 1/12h
    """
    view = navigate_to(appliance.server, 'Chargeback')

    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': 'Default'}
        })
    enterprise.computeassign()

    # Assert that the selection made is listed on the UI
    assign_view = view.browser.create_view(AssignmentsView)
    row = assign_view.selections.row(name='Enterprise')
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'


def test_assign_compute_provider(appliance, virtualcenter_provider):
    """
    Polarion:
        assignee: nachandr
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
    """
    view = navigate_to(appliance.server, 'Chargeback')

    compute_provider = cb.Assign(
        assign_to='Selected Providers',
        selections={
            virtualcenter_provider.name: {'Rate': 'Default'}
        })
    compute_provider.computeassign()

    assign_view = view.browser.create_view(AssignmentsView)
    row = assign_view.selections.row(name=virtualcenter_provider.name)
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'


def test_assign_compute_cluster(appliance, virtualcenter_provider):
    """
    Polarion:
        assignee: nachandr
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
    """
    view = navigate_to(appliance.server, 'Chargeback')

    cluster_name = "{}/{}".format(virtualcenter_provider.name,
                                  random.choice(virtualcenter_provider.data["clusters"]))

    cluster = cb.Assign(
        assign_to='Selected Cluster / Deployment Roles',
        selections={
            cluster_name: {'Rate': 'Default'}
        })
    cluster.computeassign()

    assign_view = view.browser.create_view(AssignmentsView)

    row = assign_view.selections.row(name=cluster_name)
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'


def test_assign_compute_taggedvm(appliance, virtualcenter_provider):
    """
    Polarion:
        assignee: nachandr
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
    """
    view = navigate_to(appliance.server, 'Chargeback')

    tagged_vm = cb.Assign(
        assign_to="Tagged VMs and Instances",
        tag_category="Location",
        selections={
            'Chicago': {'Rate': 'Default'}
        })
    tagged_vm.computeassign()

    assign_view = view.browser.create_view(AssignmentsView)
    row = assign_view.selections.row(name='Chicago')
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'


@pytest.mark.meta(blockers=[1273654])
def test_assign_storage_enterprise(appliance, virtualcenter_provider):
    """
    Polarion:
        assignee: nachandr
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
    """
    view = navigate_to(appliance.server, 'Chargeback')

    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': 'Default'}
        })

    enterprise.storageassign()

    assign_view = view.browser.create_view(AssignmentsView)
    row = assign_view.selections.row(name='Enterprise')
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'


def test_assign_storage_datastores(appliance, virtualcenter_provider):
    """
    Polarion:
        assignee: nachandr
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
    """
    view = navigate_to(appliance.server, 'Chargeback')

    datastore = random.choice(virtualcenter_provider.data["datastores"])["name"]

    sel_datastore = cb.Assign(
        assign_to="Selected Datastores",
        selections={
            datastore: {'Rate': 'Default'}
        })
    sel_datastore.storageassign()

    assign_view = view.browser.create_view(AssignmentsView)
    row = assign_view.selections.row(name=datastore)
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'


def test_assign_storage_tagged_datastores(appliance, virtualcenter_provider):
    """
    Polarion:
        assignee: nachandr
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
    """
    view = navigate_to(appliance.server, 'Chargeback')

    tagged_datastore = cb.Assign(
        assign_to="Tagged Datastores",
        tag_category="Location",
        selections={
            'Chicago': {'Rate': 'Default'}
        })
    tagged_datastore.storageassign()

    assign_view = view.browser.create_view(AssignmentsView)
    row = assign_view.selections.row(name='Chicago')
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'
