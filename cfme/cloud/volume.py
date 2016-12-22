# -*- coding: utf-8 -*-

from functools import partial

from navmazing import NavigateToSibling

import cfme.fixtures.pytest_selenium as sel
from cfme.exceptions import DestinationNotFound
from cfme.web_ui import (match_location, Form, InfoBlock, Input, PagedTable,
                         Select, summary_title, toolbar as tb)
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import (CFMENavigateStep, navigator,
                                                navigate_to)
from utils.version import current_version

match_volumes = partial(match_location, controller='cloud_volume',
                        title='Cloud Volumes')
match_provider = partial(match_location, controller='ems_cloud',
                         title='Cloud Providers')

creation_form = Form([
    ('volume_name', "//input[@name='name']"),
    ('volume_size', "//input[@name='size']"),
    ('cloud_tenant', Select("//select[@id='cloud_tenant_id']"))
])

_device_input = ('device_path', Input('device_path'))
_select_vm = ('select_vm', Select("//select[@id='vm_id']"))
_select_volume = ('select_volume', Select("//select[@id='volume_id']"))

attach_inst_page_form = Form([_device_input, _select_volume])
attach_vlm_page_form = Form([_device_input, _select_vm])
detach_inst_page_form = Form([_select_volume])
detach_vlm_page_form = Form([_select_vm])

list_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")


def check_version():
    if current_version() >= '5.7':
        raise DestinationNotFound('Cloud Volumes does not exist in CFME 5.7+')


def get_volume_name():
    """Returns the name of volume which page is opened"""
    return summary_title().split()[0]


class Volume(Navigatable):
    def __init__(self, name, provider, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.provider = provider


@navigator.register(Volume, 'All')
class All(CFMENavigateStep):
    def prerequisite(self):
        check_version()
        navigate_to(self.obj.appliance.server, 'LoggedIn')

    def am_i_here(self):
        return match_volumes(summary='Cloud Volumes')

    def step(self, *args, **kwargs):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Clouds', 'Volumes')(None)


@navigator.register(Volume, 'AllByProvider')
class AllByProvider(CFMENavigateStep):
    def prerequisite(self):
        check_version()
        navigate_to(self.obj.appliance.server, 'LoggedIn')

    def am_i_here(self):
        return match_provider(summary='{} (All Cloud Volumes)'.format(self.obj.provider.name))

    def step(self):
        navigate_to(self.obj.provider, 'Details')
        sel.click(InfoBlock('Relationships', 'Cloud volumes').element)


@navigator.register(Volume, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_volumes(summary='{} (Summary)'.format(self.obj.name))

    def step(self, *args, **kwargs):
        tb.select('List View')
        sel.click(list_tbl.find_row_by_cell_on_all_pages(
            {'Name': self.obj.name, 'Cloud Provider': self.obj.provider.name}))
