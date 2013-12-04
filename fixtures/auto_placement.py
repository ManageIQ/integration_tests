# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
from unittestzero import Assert


@pytest.fixture(scope="module",  # IGNORE:E1101
               params=["linux_template_workflow"])
def auto_placement_setup_data(request, cfme_data):
    '''Returns data for Provisioning Scope'''
    param = request.param
    return cfme_data.data["provisioning"][param]


@pytest.fixture
def setup_auto_placement_host(infra_hosts_pg,
        auto_placement_setup_data):
    '''Sets up Host for auto-placement'''
    infra_hosts_pg.select_host(auto_placement_setup_data['host'])
    edit_tags_for_prov_all(infra_hosts_pg)


@pytest.fixture
def setup_auto_placement_datastore(infra_datastores_pg,
        auto_placement_setup_data):
    '''Sets up Datastore for auto-placement'''
    infra_datastores_pg.select_datastore(auto_placement_setup_data['datastore'])
    edit_tags_for_prov_all(infra_datastores_pg)


def edit_tags_for_prov_all(infra_pg):
    ''' Sets up Provisioning Scope - All tags'''
    tag_cat = 'Provisioning Scope'
    tag_value = 'All'
    edit_tags_pg = infra_pg.click_on_edit_tags()
    if not edit_tags_pg.is_tag_displayed(tag_cat, tag_value):
        edit_tags_pg.select_category(tag_cat)
        edit_tags_pg.select_value(tag_value)
        edit_tags_pg.save_tag_edits()
        Assert.true(infra_pg.flash.message.startswith('Tag edits were successfully saved'))
    else:
        edit_tags_pg.cancel_tag_edits()
