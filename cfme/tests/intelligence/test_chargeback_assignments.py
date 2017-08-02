# -*- coding: utf-8 -*-
import cfme.fixtures.pytest_selenium as sel
import cfme.intelligence.chargeback.assignments as cb
import pytest
import random

from cfme import test_requirements
from utils import version
from utils.appliance.implementations.ui import navigate_to
from random import choice
from utils.log import logger

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.chargeback
]


@pytest.mark.meta(blockers=[1273654])
def test_assign_compute_enterprise(virtualcenter_provider):
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': 'Default'}
        })
    enterprise.computeassign()

    # Assert that the selection made is listed on the UI
    selected_option = sel.text(
        cb.assign_form.selections.select_by_name("Enterprise").first_selected_option)
    assert selected_option == "Default", 'Selection does not match'


def test_assign_compute_provider(virtualcenter_provider):
    compute_provider = cb.Assign(
        assign_to=version.pick({version.LOWEST: 'Selected Cloud/Infrastructure Providers',
                            '5.7': 'Selected Providers'}),
        selections={
            virtualcenter_provider.name: {'Rate': 'Default'}
        })
    compute_provider.computeassign()

    selected_option = sel.text(
        cb.assign_form.selections.select_by_name(virtualcenter_provider.name).first_selected_option)
    assert selected_option == "Default", 'Selection does not match'


def test_assign_compute_cluster(virtualcenter_provider):
    cluster_name = random.choice(virtualcenter_provider.get_yaml_data()["clusters"])

    cluster = cb.Assign(
        assign_to=version.pick({version.LOWEST: 'Selected Clusters',
                            '5.4': 'Selected Cluster / Deployment Roles'}),
        selections={
            cluster_name: {'Rate': 'Default'}
        })
    cluster.computeassign()

    selected_option = sel.text(
        cb.assign_form.selections.select_by_name(cluster_name).first_selected_option)
    assert selected_option == "Default", 'Selection does not match'


def test_assign_compute_taggedvm(virtualcenter_provider):
    tagged_vm = cb.Assign(
        assign_to="Tagged VMs and Instances",
        tag_category="Location",
        selections={
            'Chicago': {'Rate': 'Default'}
        })
    tagged_vm.computeassign()

    selected_option = sel.text(
        cb.assign_form.selections.select_by_name("Chicago").first_selected_option)
    assert selected_option == "Default", 'Selection does not match'


@pytest.mark.meta(blockers=[1273654])
def test_assign_storage_enterprise(virtualcenter_provider):
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': 'Default'}
        })

    enterprise.storageassign()

    view = navigate_to(enterprise, 'Storage')

    for row in view.selections.rows():
        logger.info('NAME TEXT IS {}'.format(row.name.text))
        option = choice(row.rate.widget.all_options)
        logger.info('OPTION TEXT IS {}'.format(row.rate.widget.select_by_visible_text(option.text)))

    selected_option = sel.text(
        cb.assign_form.selections.select_by_name("Enterprise").first_selected_option)
    assert selected_option == "Default", 'Selection does not match'


def test_assign_storage_datastores(virtualcenter_provider):
    datastore = random.choice(virtualcenter_provider.get_yaml_data()["datastores"])["name"]

    sel_datastore = cb.Assign(
        assign_to="Selected Datastores",
        selections={
            datastore: {'Rate': 'Default'}
        })
    sel_datastore.storageassign()

    selected_option = sel.text(
        cb.assign_form.selections.select_by_name(datastore).first_selected_option)
    assert selected_option == "Default", 'Selection does not match'


def test_assign_storage_tagged_datastores(virtualcenter_provider):
    tagged_datastore = cb.Assign(
        assign_to="Tagged Datastores",
        tag_category="Location",
        selections={
            'Chicago': {'Rate': 'Default'}
        })
    tagged_datastore.storageassign()

    selected_option = sel.text(
        cb.assign_form.selections.select_by_name("Chicago").first_selected_option)
    assert selected_option == "Default", 'Selection does not match'
