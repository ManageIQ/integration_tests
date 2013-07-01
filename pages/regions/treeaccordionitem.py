'''
Created on Mar 7, 2013

@author: bcrochet
'''
# -*- coding: utf-8 -*-

# pylint: disable=C0301

from pages.regions.accordionitem import AccordionItem
from pages.regions.tree import Tree

class TreeAccordionItem(AccordionItem):
    '''
    classdocs
    '''
    
    @property
    def content(self): 
        accordion_content = AccordionItem.content.fget(self)
        # Now, we need the *actual* tree root
        tree_root = accordion_content.find_element_by_xpath('div/div/ul/li')       
        return Tree(self.testsetup, tree_root)
        
class LegacyTreeAccordionItem(TreeAccordionItem):
    '''
    classdocs
    '''
    @property
    def content(self):
        from pages.regions.tree import LegacyTree
        return LegacyTree(self.testsetup, AccordionItem.content.fget(self))