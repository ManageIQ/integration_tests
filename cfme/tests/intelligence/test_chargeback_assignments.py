# -*- coding: utf-8 -*-
import cfme.fixtures.pytest_selenium as sel
import cfme.intelligence.chargeback as cb
import cfme.web_ui.flash as flash
import pytest
import random

from utils.providers import setup_a_provider
from utils import version

pytestmark = [pytest.mark.tier(3)]


@pytest.fixture(scope="module")
def provider():
    return setup_a_provider(prov_class="infra", prov_type="virtualcenter")


@pytest.mark.meta(blockers=[1273654])
def test_assign_compute_enterprise(provider):
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            "Enterprise": "Default"
        })
    enterprise.computeassign()

    flash.assert_message_match('Rate Assignments saved')
    # Assert that the selection made is listed on the UI
    selected_option = sel.text(
        cb.assign_form.selections.select_by_name("Enterprise").first_selected_option)
    assert selected_option == "Default", 'Selection does not match'


def test_assign_compute_provider(provider):
    compute_provider = cb.Assign(
        assign_to="Selected Cloud/Infrastructure Providers",
        selections={
            provider.name: "Default"
        })
    compute_provider.computeassign()

    flash.assert_message_match('Rate Assignments saved')
    selected_option = sel.text(
        cb.assign_form.selections.select_by_name(provider.name).first_selected_option)
    assert selected_option == "Default", 'Selection does not match'


def test_assign_compute_cluster(provider):
    cluster_name = random.choice(provider.get_yaml_data()["clusters"])

    cluster = cb.Assign(
        assign_to=version.pick({version.LOWEST: 'Selected Clusters',
                            '5.4': 'Selected Cluster / Deployment Roles'}),
        selections={
            cluster_name: "Default"
        })
    cluster.computeassign()

    flash.assert_message_match('Rate Assignments saved')
    selected_option = sel.text(
        cb.assign_form.selections.select_by_name(cluster_name).first_selected_option)
    assert selected_option == "Default", 'Selection does not match'


def test_assign_compute_taggedvm(provider):
    tagged_vm = cb.Assign(
        assign_to="Tagged VMs and Instances",
        tag_category="Location",
        selections={
            "Chicago": "Default"
        })
    tagged_vm.computeassign()

    flash.assert_message_match('Rate Assignments saved')
    selected_option = sel.text(
        cb.assign_form.selections.select_by_name("Chicago").first_selected_option)
    assert selected_option == "Default", 'Selection does not match'


@pytest.mark.meta(blockers=[1273654])
def test_assign_storage_enterprise(provider):
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            "Enterprise": "Default"
        })

    enterprise.storageassign()

    flash.assert_message_match('Rate Assignments saved')
    selected_option = sel.text(
        cb.assign_form.selections.select_by_name("Enterprise").first_selected_option)
    assert selected_option == "Default", 'Selection does not match'


def test_assign_storage_datastores(provider):
    datastore = random.choice(provider.get_yaml_data()["datastores"])["name"]

    sel_datastore = cb.Assign(
        assign_to="Selected Datastores",
        selections={
            datastore: "Default"
        })
    sel_datastore.storageassign()

    flash.assert_message_match('Rate Assignments saved')
    selected_option = sel.text(
        cb.assign_form.selections.select_by_name(datastore).first_selected_option)
    assert selected_option == "Default", 'Selection does not match'


def test_assign_storage_tagged_datastores(provider):
    tagged_datastore = cb.Assign(
        assign_to="Tagged Datastores",
        tag_category="Location",
        selections={
            "Chicago": "Default"
        })
    tagged_datastore.storageassign()

    selected_option = sel.text(
        cb.assign_form.selections.select_by_name("Chicago").first_selected_option)
    assert selected_option == "Default", 'Selection does not match'
    flash.assert_message_match('Rate Assignments saved')
