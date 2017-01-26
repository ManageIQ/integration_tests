# -*- coding: utf-8 -*-
""" A model of Workloads page in CFME
"""
from functools import partial
from navmazing import NavigateToSibling, NavigateToAttribute  # NOQA

from cfme.exceptions import DestinationNotFound
from cfme.web_ui import accordion, match_location, toolbar
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep

vm_instances_tree = partial(accordion.tree, "VMs & Instances", 'All VMs & Instances')
templates_images_tree = partial(accordion.tree, "Templates & Images", 'All Templates & Images')

# Only this buttons present. may be used in future
cfg_btn = partial(toolbar.select, 'Configuration')
pol_btn = partial(toolbar.select, 'Policy')
lcl_btn = partial(toolbar.select, 'Lifecycle')

match_page = partial(match_location, controller='vm_or_template', title='Workloads')


class VmsInstances(Navigatable):
    """
        This is fake class mainly needed for navmazing navigation

    """
    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance)


class TemplatesImages(Navigatable):
    """
        This is fake class mainly needed for navmazing navigation

    """

    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance)


@navigator.register(VmsInstances, 'All')
class AllVMs(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'Workloads')
        if 'filter_folder' not in kwargs:
            vm_instances_tree()
        elif 'filter_folder' in kwargs and 'filter_name' in kwargs:
            vm_instances_tree(kwargs['filter_folder'], kwargs['filter_name'])
        else:
            raise DestinationNotFound("the destination isn't found")

    def am_i_here(self, *args, **kwargs):
        if 'filter_folder' not in kwargs:
            return match_page(summary='All VMs & Instances')
        elif 'filter_folder' in kwargs and 'filter_name' in kwargs:
            return match_page(summary='All VMs and Instances - '
                                      'Filtered by "{}" ( clear )'.format(kwargs['filter_name']))


@navigator.register(TemplatesImages, 'All')
class AllTemplates(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'Workloads')
        if 'filter_folder' not in kwargs:
            templates_images_tree()
        elif 'filter_folder' in kwargs and 'filter_name' in kwargs:
            templates_images_tree(kwargs['filter_folder'], kwargs['filter_name'])
        else:
            raise DestinationNotFound("the destination isn't found")

    def am_i_here(self, *args, **kwargs):
        if 'filter_folder' not in kwargs:
            return match_page(summary='All Templates & Images')
        elif 'filter_folder' in kwargs and 'filter_name' in kwargs:
            return match_page(summary='All VM Templates and Images - '
                                      'Filtered by "{}" ( clear )'.format(kwargs['filter_name']))
