# -*- coding: utf-8 -*-

from functools import partial

from navmazing import NavigateToSibling

import cfme.fixtures.pytest_selenium as sel
from cfme.exceptions import DestinationNotFound
from cfme.web_ui import (match_location, Form, InfoBlock, Input, PagedTable,
                         Select, summary_title, toolbar as tb)
from cfme.web_ui.form_buttons import add_ng
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

    def create(self, volume_size):
        """
        Creates cloud volume
        :param volume_size: int value of volume size to be created in GB
        """
        navigate_to(Volume, 'All')
        tb.select('Configuration', 'Add a new Cloud Volume')
        volume_data = dict(volume_name=self.name,
                           volume_size=volume_size,
                           cloud_tenant=self.provider.mgmt.list_tenant()[0])
        creation_form.fill(volume_data)
        sel.click(add_ng)

    def find_free_volume(self):
        """
        Gets first available volume on provider, returns None if there are no
            free volumes found
        :returns Volume object
        """
        for volume in self.provider.mgmt.list_volume():
            vol_info = self.provider.mgmt.get_volume(volume).to_dict()
            if vol_info['status'] == 'available':
                volume_name = vol_info['display_name']
                break
        else:
            return None
        return Volume(volume_name, self.provider)

    def delete(self):
        """Deletes 'self' volume"""
        navigate_to(Volume, 'All')
        params = {'Status': 'available',
                  'Name': self.name,
                  'Cloud Provider': self.provider.get_yaml_data()['name']}
        list_tbl.click_row_by_cells(params, 'Name')
        tb.select('Configuration', 'Delete this Cloud Volume',
                  invokes_alert=True)
        sel.handle_alert(cancel=False)


@navigator.register(Volume, 'All')
class All(CFMENavigateStep):
    def prerequisite(self):
        check_version()
        navigate_to(self.obj.appliance.server, 'LoggedIn')

    def am_i_here(self):
        return match_volumes(summary='Cloud Volumes')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Volumes')


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
