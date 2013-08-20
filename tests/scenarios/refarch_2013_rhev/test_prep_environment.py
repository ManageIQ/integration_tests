'''
CFME automation to setup reference architecture
See https://access.redhat.com/site/articles/411683
'''
# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
from unittestzero import Assert


pytestmark = [pytest.mark.usefixtures("maximized")]
FLASH_MESSAGE_NOT_MATCHED = 'Flash message did not match expected value'


def test_tag_providers(infra_providers_pg, provider):
    '''Tag management systems to prepare for provisioning
    '''
    infra_providers_pg.select_provider(provider["name"])
    edit_tags_pg = infra_providers_pg.click_on_edit_tags()
    for tag in provider["tags"]:
        _value = provider["tags"][tag]
        edit_tags_pg.select_category(tag)
        edit_tags_pg.select_value(_value)
        Assert.true(edit_tags_pg.is_tag_displayed(tag, _value))
    edit_tags_pg.save_tag_edits()
    Assert.contains(
        'Tag edits were successfully saved',
        edit_tags_pg.flash.message,
        FLASH_MESSAGE_NOT_MATCHED)


def test_tag_clusters(infra_clusters_pg, provider, cluster):
    '''Tag clusters to prepare for provisioning
    '''
    infra_clusters_pg.select_cluster(cluster)
    edit_tags_pg = infra_clusters_pg.click_on_edit_tags()
    for tag in provider["tags"]:
        _value = provider["tags"][tag]
        edit_tags_pg.select_category(tag)
        edit_tags_pg.select_value(_value)
        Assert.true(edit_tags_pg.is_tag_displayed(tag, _value))
    edit_tags_pg.save_tag_edits()
    Assert.contains(
        'Tag edits were successfully saved',
        edit_tags_pg.flash.message,
        FLASH_MESSAGE_NOT_MATCHED)


def test_tag_hosts(infra_hosts_pg, provider, host):
    '''Tag hosts to prepare for provisioning
    '''
    infra_hosts_pg.select_host(host["name"])
    edit_tags_pg = infra_hosts_pg.click_on_edit_tags()
    for tag in provider["tags"]:
        _value = provider["tags"][tag]
        edit_tags_pg.select_category(tag)
        edit_tags_pg.select_value(_value)
        Assert.true(edit_tags_pg.is_tag_displayed(tag, _value))
    edit_tags_pg.save_tag_edits()
    Assert.contains(
        'Tag edits were successfully saved',
        edit_tags_pg.flash.message,
        FLASH_MESSAGE_NOT_MATCHED)


def test_tag_datastores(infra_datastores_pg, provider, datastore):
    '''Tag datastores to prepare for provisioning
    '''
    infra_datastores_pg.select_datastore(datastore)
    edit_tags_pg = infra_datastores_pg.click_on_edit_tags()
    for tag in provider["tags"]:
        _value = provider["tags"][tag]
        edit_tags_pg.select_category(tag)
        edit_tags_pg.select_value(_value)
        Assert.true(edit_tags_pg.is_tag_displayed(tag, _value))
    edit_tags_pg.save_tag_edits()
    Assert.contains(
        'Tag edits were successfully saved',
        edit_tags_pg.flash.message,
        FLASH_MESSAGE_NOT_MATCHED)


def test_edit_cfme_server_relationship(infra_vms_pg, appliance):
    '''Set the CFME server relationship
    '''
    vm_pg = infra_vms_pg.find_vm_page(appliance['vm_name'], None, False, True)
    vm_pg = vm_pg.edit_cfme_relationship_and_save(appliance['appliance_name'])
    Assert.equal(vm_pg.flash.message, "Management Engine Relationship saved",
        FLASH_MESSAGE_NOT_MATCHED)


def test_set_template_ownership(infra_vms_pg, provision):
    '''Set template ownership
    '''
    vm_pg = infra_vms_pg.find_vm_page(provision['template'], None, False, True)
    vm_pg = vm_pg.set_ownership_and_save(provision['user'])
    Assert.equal(vm_pg.flash.message, "Ownership saved for selected VMs",
        FLASH_MESSAGE_NOT_MATCHED)
