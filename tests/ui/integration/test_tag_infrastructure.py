#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
from pages.login import LoginPage

@pytest.fixture(scope="module", # IGNORE:E1101
                params=["vsphere5", "rhevm31"]) 
def management_system(request, cfme_data):
    param = request.param
    return cfme_data.data["management_systems"][param]

@pytest.mark.nondestructive  # IGNORE:E1101
@pytest.mark.usefixtures("maximized", "setup_mgmt_systems")
class TestInfrastructureTags:
    def test_tag_management_systems(self, mozwebqa, home_page_logged_in, management_system):
        """Tag management systems to prepare for provisioning
        """
        ms_pg = home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
        Assert.true(ms_pg.is_the_current_page)
        ms_pg.select_management_system(management_system["name"])
        edit_tags_pg = ms_pg.click_on_edit_tags()
        for tag in management_system["tags"]:
            _value = management_system["tags"][tag]
            edit_tags_pg.select_category(tag)
            edit_tags_pg.select_value(_value)
            Assert.true(edit_tags_pg.is_tag_displayed(tag, _value))
        edit_tags_pg.save
        Assert.true(edit_tags_pg.flash.message.startswith('Tag edits were successfully saved'))

    def test_tag_clusters(self, mozwebqa, home_page_logged_in, management_system):
        """Tag clusters to prepare for provisioning

           Only required for RHEV
        """
        cluster_pg = home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Clusters").click()
        Assert.true(cluster_pg.is_the_current_page)
        for cluster in management_system["clusters"]:
            cluster_pg.select_cluster(cluster)
        edit_tags_pg = cluster_pg.click_on_edit_tags()
        for tag in management_system["tags"]:
            _value = management_system["tags"][tag]
            edit_tags_pg.select_category(tag)
            edit_tags_pg.select_value(_value)
            Assert.true(edit_tags_pg.is_tag_displayed(tag, _value))
        edit_tags_pg.save
        Assert.true(edit_tags_pg.flash.message.startswith('Tag edits were successfully saved'))

    def test_tag_hosts(self, mozwebqa, home_page_logged_in, management_system):
        """Tag hosts to prepare for provisioning
        """
        hosts_pg = home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Hosts").click()
        Assert.true(hosts_pg.is_the_current_page)
        for host in management_system["hosts"]:
            hosts_pg.select_host(host["name"])
        edit_tags_pg = hosts_pg.click_on_edit_tags()
        for tag in management_system["tags"]:
            _value = management_system["tags"][tag]
            edit_tags_pg.select_category(tag)
            edit_tags_pg.select_value(_value)
            Assert.true(edit_tags_pg.is_tag_displayed(tag, _value))
        edit_tags_pg.save
        Assert.true(edit_tags_pg.flash.message.startswith('Tag edits were successfully saved'))

    def test_tag_datastores(self, mozwebqa, home_page_logged_in, management_system):
        """Tag datastores to prepare for provisioning
        """
        ds_pg = home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Datastores").click()
        Assert.true(ds_pg.is_the_current_page)
        for datastore in management_system["datastores"]:
            ds_pg.select_datastore(datastore)
        edit_tags_pg = ds_pg.click_on_edit_tags()
        for tag in management_system["tags"]:
            _value = management_system["tags"][tag]
            edit_tags_pg.select_category(tag)
            edit_tags_pg.select_value(_value)
            Assert.true(edit_tags_pg.is_tag_displayed(tag, _value))
        edit_tags_pg.save
        Assert.true(edit_tags_pg.flash.message.startswith('Tag edits were successfully saved'))

