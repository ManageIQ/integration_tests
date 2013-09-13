# -*- coding: utf-8 -*-
# pylint: disable=C0103
# pylint: disable=R0904

import re
from pages.regions.quadiconitem import QuadiconItem

class InstanceQuadIcon(QuadiconItem):
    @property
    def os(self):
        image_src = self._root_element.find_element(
            *self._quad_tl_locator).find_element_by_tag_name(
                "img").get_attribute("src")
        return re.search('.+/os-(.+)\.png', image_src).group(1)

    @property
    def current_state(self):
        image_src = self._root_element.find_element(
            *self._quad_tr_locator).find_element_by_tag_name(
                "img").get_attribute("src")
        return re.search('.+/currentstate-(.+)\.png', image_src).group(1)

    @property
    def vendor(self):
        image_src = self._root_element.find_element(
            *self._quad_bl_locator).find_element_by_tag_name(
                "img").get_attribute("src")
        return re.search('.+/vendor-(.+)\.png', image_src).group(1)

    @property
    def snapshots(self):
        return self._root_element.find_element(*self._quad_br_locator).text

    def click(self):
        self._root_element.click()
        self._wait_for_results_refresh()
        from pages.cloud.instances.details import Details
        return Details(self.testsetup)
