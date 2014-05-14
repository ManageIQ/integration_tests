# -*- coding: utf-8 -*-
# pylint: disable=E1101

import pytest
import time
from unittestzero import Assert
from pages.login import LoginPage

pytestmark = [pytest.mark.nondestructive,
              pytest.mark.usefixtures("setup_infrastructure_providers") ]

@pytest.mark.usefixtures("maximized")
class TestInfrastructureTags:

    def _finish_add_test(self, edit_tags_pg):
        """Finish adding tag test
        """
        tag_cat, tag_value = edit_tags_pg.add_random_tag()
        Assert.true(edit_tags_pg.is_tag_displayed(tag_cat, tag_value))
        edit_tags_pg.save_tag_edits()
        Assert.true(edit_tags_pg.flash.message.startswith(
                'Tag edits were successfully saved'))

    def test_tag_provider(self, infra_providers_pg):
        """Add a tag to a provider
        """
        infra_providers_pg.quadicon_region.mark_random_quadicon_checkbox()
        edit_tags_pg = infra_providers_pg.click_on_edit_tags()
        self._finish_add_test(edit_tags_pg)

    def test_tag_cluster(self, infra_clusters_pg):
        """Add a tag to a cluster
        """
        infra_clusters_pg.icon.mark_random_quadicon_checkbox()
        edit_tags_pg = infra_clusters_pg.click_on_edit_tags()
        self._finish_add_test(edit_tags_pg)

    def test_tag_host(self, infra_hosts_pg):
        """Add a tag to a host
        """
        infra_hosts_pg.quadicon_region.mark_random_quadicon_checkbox()
        edit_tags_pg = infra_hosts_pg.click_on_edit_tags()
        self._finish_add_test(edit_tags_pg)

    def test_tag_datastore(self, infra_datastores_pg):
        """Add a tag to a datastore
        """
        infra_datastores_pg.quadicon_region.mark_random_quadicon_checkbox()
        edit_tags_pg = infra_datastores_pg.click_on_edit_tags()
        self._finish_add_test(edit_tags_pg)

    def test_tag_vm(self, infra_vms_pg):
        """Add a tag to a vm
        """
        infra_vms_pg.quadicon_region.mark_random_quadicon_checkbox()
        edit_tags_pg = infra_vms_pg.click_on_edit_tags()
        self._finish_add_test(edit_tags_pg)

    def test_tag_template(self, infra_providers_pg):
        """Add a tag to a template
        """
        prov_pg = infra_providers_pg.quadicon_region.click_random_quadicon()
        temp_pg = prov_pg.all_templates()
        temp_pg.view_buttons.change_to_grid_view()
        temp_pg.quadicon_region.click_random_quadicon()
        edit_tags_pg = temp_pg.click_on_edit_tags()
        self._finish_add_test(edit_tags_pg)

    def test_remove_tag(self, infra_providers_pg):
        """Add a tag to a template
        """
        # go to just provider vms, had issue with duplicate (archived) vms otherwise
        prov_pg = infra_providers_pg.quadicon_region.click_random_quadicon()
        infra_vms_pg = prov_pg.all_vms()

        title = infra_vms_pg.quadicon_region.mark_random_quadicon_checkbox()
        edit_tags_pg = infra_vms_pg.click_on_edit_tags()

        tag_cat, tag_value = edit_tags_pg.add_random_tag()
        Assert.true(edit_tags_pg.is_tag_displayed(tag_cat, tag_value))
        edit_tags_pg.save_tag_edits()

        infra_vms_pg.quadicon_region.mark_icon_checkbox([title])
        edit_tags_pg = infra_vms_pg.click_on_edit_tags()

        edit_tags_pg.delete_tag(tag_cat)
        edit_tags_pg.save_tag_edits()

        infra_vms_pg.quadicon_region.mark_icon_checkbox([title])
        edit_tags_pg = infra_vms_pg.click_on_edit_tags()
        Assert.false(edit_tags_pg.is_tag_displayed(tag_cat, tag_value))

    def test_unable_to_add_same_tag(self, infra_providers_pg):
        """Add a tag to a template
        """
        # go to just provider vms, had issue with duplicate (archived) vms otherwise
        prov_pg = infra_providers_pg.quadicon_region.click_random_quadicon()
        infra_vms_pg = prov_pg.all_vms()

        title = infra_vms_pg.quadicon_region.mark_random_quadicon_checkbox()
        edit_tags_pg = infra_vms_pg.click_on_edit_tags()

        tag_cat, tag_value = edit_tags_pg.add_random_tag()
        Assert.true(edit_tags_pg.is_tag_displayed(tag_cat, tag_value))
        edit_tags_pg.save_tag_edits()

        infra_vms_pg.quadicon_region.mark_icon_checkbox([title])
        edit_tags_pg = infra_vms_pg.click_on_edit_tags()

        if tag_cat in edit_tags_pg.available_categories:
            Assert.true(tag_value not in edit_tags_pg.category_values(tag_cat))

    #TODO:
    #def test_tag_multiple_objects
    #def test_edit_tag_reset
    #def test_edit_tag_cancel
    #def test_all_values_are_assigned
