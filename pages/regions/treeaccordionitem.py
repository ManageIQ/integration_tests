'''
Created on Mar 7, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.regions.accordionitem import AccordionItem
from pages.regions.tree import Tree

class TreeAccordionItem(AccordionItem):
    '''
    classdocs
    '''
    
    def __init__(self,setup,accordion_element):
        AccordionItem.__init__(self, setup, accordion_element)
        # TODO: Add more initialization here

    @property
    def content(self):        
        return Tree(self.testsetup,AccordionItem.content.fget(self)) #@UndefinedVariable
        