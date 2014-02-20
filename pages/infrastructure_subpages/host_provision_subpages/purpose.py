# -*- coding: utf-8 -*-

from pages.base import Base
from pages.infrastructure_subpages.host_provision import HostProvisionFormButtonMixin
from selenium.webdriver.common.by import By


class HostProvisionPurpose(Base, HostProvisionFormButtonMixin):
    '''Models the Purpose subpage in the Provision wizard'''
   # _tag_tree_locator = (By.CSS_SELECTOR, "div#all_tags_treebox")
    _tag_tree_locator = (By.ID, "all_tags_treebox")

    @property
    def tag_tree(self):
        from pages.regions.tree import Tree
        #the_tree = Tree(self.testsetup, *self._tag_tree_locator)
        tree_element = self.get_element(*self._tag_tree_locator)
        the_tree = Tree(self.testsetup, tree_element)
        the_tree._main_tree_item_locator = self._tag_tree_locator
        return the_tree

    def click_on_nodes(self, node1, node2):
        self.tag_tree.find_node_by_name(node1).click()
        self.tag_tree.find_node_by_name(node1).twisty.expand()
        self._wait_for_results_refresh()
        self.tag_tree.find_node_by_name(node2).click()
        self._wait_for_results_refresh()
        return self.tag_tree

