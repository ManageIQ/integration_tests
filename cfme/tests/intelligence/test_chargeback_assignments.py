# -*- coding: utf-8 -*-
import pytest
import random

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to, navigator

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.chargeback
]


@pytest.mark.meta(blockers=[1273654])
def test_assign_compute_enterprise(appliance, assigns_collection, virtualcenter_provider):
    view = navigate_to(appliance.server, 'Chargeback')

    enterprise = assigns_collection.instantiate(assign_to="The Enterprise", selections={
            'Enterprise': {'Rate': 'Default'}
        })
    enterprise.computeassign()

    # Assert that the selection made is listed on the UI
    assign_view = view.browser.create_view(navigator.get_class(assigns_collection, "Compute").VIEW)
    row = assign_view.selections.row(name='Enterprise')
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'


def test_assign_compute_provider(appliance, virtualcenter_provider, assigns_collection):
    view = navigate_to(appliance.server, 'Chargeback')

    compute_provider = assigns_collection.instantiate(
        assign_to='Selected Providers',
        selections={
            virtualcenter_provider.name: {'Rate': 'Default'}
        })
    compute_provider.computeassign()

    assign_view = view.browser.create_view(navigator.get_class(assigns_collection, "Compute").VIEW)
    row = assign_view.selections.row(name=virtualcenter_provider.name)
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'


def test_assign_compute_cluster(appliance, virtualcenter_provider, assigns_collection):
    view = navigate_to(appliance.server, 'Chargeback')

    cluster_name = "{}/{}".format(virtualcenter_provider.name,
                                  random.choice(virtualcenter_provider.data["clusters"]))

    cluster = assigns_collection.instantiate(
        assign_to='Selected Cluster / Deployment Roles',
        selections={
            cluster_name: {'Rate': 'Default'}
        })
    cluster.computeassign()

    assign_view = view.browser.create_view(navigator.get_class(assigns_collection, "Compute").VIEW)

    row = assign_view.selections.row(name=cluster_name)
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'


def test_assign_compute_taggedvm(appliance, assigns_collection):
    view = navigate_to(appliance.server, 'Chargeback')

    tagged_vm = assigns_collection.instantiate(
        assign_to="Tagged VMs and Instances",
        tag_category="Location",
        selections={
            'Chicago': {'Rate': 'Default'}
        })
    tagged_vm.computeassign()

    assign_view = view.browser.create_view(navigator.get_class(assigns_collection, "Compute").VIEW)
    row = assign_view.selections.row(name='Chicago')
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'


@pytest.mark.meta(blockers=[1273654])
def test_assign_storage_enterprise(appliance, assigns_collection):
    view = navigate_to(appliance.server, 'Chargeback')

    enterprise = assigns_collection.instantiate(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': 'Default'}
        })

    enterprise.storageassign()

    assign_view = view.browser.create_view(navigator.get_class(assigns_collection, "Compute").VIEW)
    row = assign_view.selections.row(name='Enterprise')
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'


def test_assign_storage_datastores(appliance, virtualcenter_provider, assigns_collection):
    view = navigate_to(appliance.server, 'Chargeback')

    datastore = random.choice(virtualcenter_provider.data["datastores"])["name"]

    sel_datastore = assigns_collection.instantiate(
        assign_to="Selected Datastores",
        selections={
            datastore: {'Rate': 'Default'}
        })
    sel_datastore.storageassign()

    assign_view = view.browser.create_view(navigator.get_class(assigns_collection, "Compute").VIEW)
    row = assign_view.selections.row(name=datastore)
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'


def test_assign_storage_tagged_datastores(appliance, assigns_collection):
    view = navigate_to(appliance.server, 'Chargeback')

    tagged_datastore = assigns_collection.instantiate(
        assign_to="Tagged Datastores",
        tag_category="Location",
        selections={
            'Chicago': {'Rate': 'Default'}
        })
    tagged_datastore.storageassign()

    assign_view = view.browser.create_view(navigator.get_class(assigns_collection, "Compute").VIEW)
    row = assign_view.selections.row(name='Chicago')
    selected_option = row.rate.widget.selected_option
    assert selected_option == "Default", 'Selection does not match'
