#!/usr/bin/env python

# -*- coding: utf-8 -*-
# pylint: disable=E1101
import pytest
import time
from unittestzero import Assert
from pages.login import LoginPage

@pytest.fixture(scope="module",
                params=["vsphere5", "rhevm31"])
def provider(request, cfme_data):
    param = request.param
    return cfme_data.data["management_systems"][param]

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized", "setup_infrastructure_providers")
class TestInfrastructureTags:
    def test_tag_providers(self, infra_providers_pg, provider):
        """Tag management systems to prepare for provisioning
        """
        Assert.true(infra_providers_pg.is_the_current_page)
        infra_providers_pg.select_provider(provider["name"])
        edit_tags_pg = infra_providers_pg.click_on_edit_tags()
        for tag in provider["tags"]:
            _value = provider["tags"][tag]
            edit_tags_pg.select_category(tag)
            edit_tags_pg.select_value(_value)
            Assert.true(edit_tags_pg.is_tag_displayed(tag, _value))
        edit_tags_pg.save_tag_edits()
        Assert.true(edit_tags_pg.flash.message.startswith(
                'Tag edits were successfully saved'))

    def test_tag_clusters(self,infra_clusters_pg, provider):
        """Tag clusters to prepare for provisioning

           Only required for RHEV
        """
        Assert.true(infra_clusters_pg.is_the_current_page)
        for cluster in provider["clusters"]:
            infra_clusters_pg.select_cluster(cluster)
        edit_tags_pg = infra_clusters_pg.click_on_edit_tags()
        for tag in provider["tags"]:
            _value = provider["tags"][tag]
            edit_tags_pg.select_category(tag)
            edit_tags_pg.select_value(_value)
            Assert.true(edit_tags_pg.is_tag_displayed(tag, _value))
        edit_tags_pg.save_tag_edits()
        Assert.true(edit_tags_pg.flash.message.startswith(
                'Tag edits were successfully saved'))

    def test_tag_hosts(self, infra_hosts_pg, provider):
        """Tag hosts to prepare for provisioning
        """
        Assert.true(infra_hosts_pg.is_the_current_page)
        for host in provider["hosts"]:
            infra_hosts_pg.select_host(host["name"])
        edit_tags_pg = infra_hosts_pg.click_on_edit_tags()
        for tag in provider["tags"]:
            _value = provider["tags"][tag]
            edit_tags_pg.select_category(tag)
            edit_tags_pg.select_value(_value)
            Assert.true(edit_tags_pg.is_tag_displayed(tag, _value))
        edit_tags_pg.save_tag_edits()
        Assert.true(edit_tags_pg.flash.message.startswith(
                'Tag edits were successfully saved'))

    def test_tag_datastores(self, infra_datastores_pg, provider):
        """Tag datastores to prepare for provisioning
        """
        Assert.true(infra_datastores_pg.is_the_current_page)
        for datastore in provider["datastores"]:
            infra_datastores_pg.select_datastore(datastore)
        edit_tags_pg = infra_datastores_pg.click_on_edit_tags()
        for tag in provider["tags"]:
            _value = provider["tags"][tag]
            edit_tags_pg.select_category(tag)
            edit_tags_pg.select_value(_value)
            Assert.true(edit_tags_pg.is_tag_displayed(tag, _value))
        edit_tags_pg.save_tag_edits()
        Assert.true(edit_tags_pg.flash.message.startswith(
                'Tag edits were successfully saved'))

