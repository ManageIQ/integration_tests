# -*- coding: utf-8 -*-
'''
Created on Mar 7, 2013

@author: bcrochet
'''


from pages.page import Page
from selenium.webdriver.common.by import By
import re

class Tree(Page):
    '''
    classdocs
    '''
    _main_tree_item_locator = (By.CSS_SELECTOR, 'ul')
    _tree_items_locator = (By.CSS_SELECTOR, 'li')
    _tree_items_children_locator = (By.XPATH, 'ul/li')
    _tree_item_name_locator = (By.CSS_SELECTOR, 'a')

    def __init__(self,setup,root_element,parent = None):
        Page.__init__(self, setup, root_element)
        self._parent = parent

    @property
    def root(self):
        return self._root_element

    @property
    def children(self):
        child_elements = self._root_element.find_elements(
                *self._tree_items_children_locator)
        # Remaining tree item elements are children, instantiate them as
        # the same type as self to support different tree types in subclasses
        return [type(self)(self.testsetup, element, self)
                for element in child_elements]

    @property
    def twisty(self):
        from pages.regions.twisty import Twisty
        return Twisty(self.testsetup, self.root)

    @property
    def name(self):
        return self.root.find_element(
                *self._tree_item_name_locator).text.encode('utf-8')  

    @property
    def parent(self):
        return self._parent

    def is_displayed(self):
        return self.root.is_displayed()

    def click(self):
        element = self.root.click()
        self._wait_for_results_refresh()
        return element

    def find_node_by_regexp(self, regexp_str):
        # finds first node by name in the whole tree, breadth first
        regexp = re.compile(regexp_str)
        queue = [self]
        while queue:
            node = queue.pop(0)
            if regexp.match(node.name):
                return node
            else:
                node.twisty.expand()
                queue.extend(node.children)

    def find_node_by_name(self, name):
        return self.find_node_by_regexp(r"\A%s\Z" % re.escape(name))

    def find_node_by_substr(self, name):
        return self.find_node_by_regexp(re.escape(name))

class LegacyTree(Tree):
    '''Override of the tree to support DynaTree'''
    _main_tree_item_locator = (By.CSS_SELECTOR, 
            "table > tbody > tr > td > table > tbody")
    _tree_items_locator = (By.XPATH, "tr")

    @property
    def twisty(self):
        from pages.regions.twisty import LegacyTwisty
        return LegacyTwisty(self.testsetup, self.root)

    @property
    def name(self):
        return self.root.text.encode('utf-8')

    @property
    def root(self):
        # First tree item element is the root
        return self._root_element.find_element(
               *self._main_tree_item_locator).find_element(
                       *self._tree_items_locator)

    @property
    def children(self):
        tree_element =  self._root_element.find_element(
                *self._main_tree_item_locator)
        child_elements = tree_element.find_elements(*self._tree_items_locator)
        # Pop off the root element, iterate over the rest
        child_elements.pop(0)
        # Remaining tree item elements are children, instantiate them as
        # the same type as self to support different tree types in subclasses
        return [type(self)(self.testsetup, element, self)
                for element in child_elements]


class NewTree(Page):
    """ Modified tree structure for Control / Explorer and possibly others.

    @author: Milan Falešník <mfalesni@redhat.com>
    """
    _caption_element_locator = "span"
    _caption_element_text_locator = "span > a"
    _caption_element_image_locator = "span > img"
    _caption_element_expander_locator = "span > span"

    _child_nodes_locator = "ul > li"

    def __init__(self, setup, root_element, parent=None):
        Page.__init__(self, setup, root_element)
        self._parent = parent

    @property
    def root(self):
        return self._root_element

    @property
    def children(self):
        child_elements = self.root.find_elements_by_css_selector(self._child_nodes_locator)
        return [type(self)(self.testsetup, element, self)
                for element
                in child_elements]

    @property
    def caption_root(self):
        """ Element encapsulating the row with text, image and expander

        """
        return self.root.find_element_by_css_selector(self._caption_element_locator)

    @property
    def expander(self):
        """ Element used to expand the child tree

        """
        return self.root.find_element_by_css_selector(self._caption_element_expander_locator)

    @property
    def link(self):
        """ Element with link and text

        """
        return self.root.find_element_by_css_selector(self._caption_element_text_locator)

    @property
    def image(self):
        """ Element with the image

        """
        return self.root.find_element_by_css_selector(self._caption_element_image_locator)

    @property
    def is_expanded(self):
        """ Is it already expanded?

        """
        return "dynatree-expanded" in self.caption_root.get_attribute("class")

    @property
    def is_expandable(self):
        """ Can it be expanded?

        """
        return "dynatree-expander" in self.expander.get_attribute("class")

    @property
    def name(self):
        """ Displayed text

        """
        return self.link.text.encode('utf-8')

    @property
    def parent(self):
        return self._parent

    def is_displayed(self):
        return self.root.is_displayed()

    def click(self):
        element = self.link.click()
        self._wait_for_results_refresh()
        return element

    def expand(self):
        """ Click on expander

        """
        element = self.expander.click()
        self._wait_for_results_refresh()
        return element

    def find_node_by_regexp(self, regexp_str, img_src_contains=None):
        # finds first node by name in the whole tree, breadth first
        regexp = re.compile(regexp_str)
        queue = [self]
        while queue:
            node = queue.pop(0)
            if regexp.match(node.name):
                if img_src_contains and img_src_contains not in node.image.get_attribute("src"):
                    continue
                return node
            elif node.is_expandable:
                if not node.is_expanded:
                    node.expand()
                queue.extend(node.children)

    def find_node_by_name(self, name, img_src_contains=None):
        return self.find_node_by_regexp(r"\A%s\Z" % re.escape(name),
                img_src_contains=img_src_contains)

    def find_node_by_substr(self, name, img_src_contains=None):
        return self.find_node_by_regexp(re.escape(name),
                img_src_contains=img_src_contains)

    def get_node(self, path):
        # path = "Compliance Policies/Host Compliance Policies::asdf"
        # Do not write the root element
        path, node_name = path.rsplit("::", 1)
        for node in self.get_nodes(path):
            if node.name.strip() == node_name.strip():
                return node

    def get_nodes(self, path):
        # path = "Compliance Policies/Host Compliance Policies"
        # Do not write the root element
        this = self
        path = path.split("/")
        while path:
            field = path.pop(0)
            assert this.is_expandable, "Element %s is not expandable!" % field.name
            if not this.is_expanded:
                this.expand()
            found = False
            for item in this.children:
                if item.name.strip() == field.strip():
                    print "tu su", item.name, field
                    this = item
                    found = True
                    break
            if not found:
                raise Exception("Item %s not found!" % field)
            
        return this.children
