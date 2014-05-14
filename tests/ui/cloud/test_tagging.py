# -*- coding: utf-8 -*-
# pylint: disable=E1101

import pytest
import time
from unittestzero import Assert
from pages.login import LoginPage

pytestmark = [pytest.mark.nondestructive,
              pytest.mark.usefixtures("setup_cloud_providers") ]

@pytest.mark.usefixtures("maximized")
class TestCloudTags:

    def _finish_add_test(self, edit_tags_pg):
        """Finish adding tag test
        """
        tag_cat, tag_value = edit_tags_pg.add_random_tag()
        Assert.true(edit_tags_pg.is_tag_displayed(tag_cat, tag_value))
        edit_tags_pg.save_tag_edits()
        Assert.true(edit_tags_pg.flash.message.startswith(
                'Tag edits were successfully saved'))

    def test_tag_provider(self, cloud_providers_pg):
        """Add a tag to a provider
        """
        cloud_providers_pg.quadicon_region.mark_random_quadicon_checkbox()
        edit_tags_pg = cloud_providers_pg.click_on_edit_tags()
        self._finish_add_test(edit_tags_pg)

    #TODO:
    #def test_tag_av_zone
    #def test_tag_flavor
    #def test_tag_instance
    #def test_tag_image
    #def test_remove_tag
    #def test_unable_to_add_same_tag
    #def test_tag_multiple_objects
    #def test_edit_tag_reset
    #def test_edit_tag_cancel
    #def test_all_values_are_assigned
