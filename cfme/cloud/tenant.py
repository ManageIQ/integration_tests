""" Page functions for Tenant pages


:var list_page: A :py:class:`cfme.web_ui.Region` object describing elements on the list page.
:var details_page: A :py:class:`cfme.web_ui.Region` object describing elements on the detail page.
"""

from utils.conf import cfme_data
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Region
from cfme.web_ui.tables import Table, Split

# Page specific locators
list_page = Region(
    locators={
        'tenant_table': Table.create(Split(
            '//div[@class="xhdr"]/table/tbody',
            '//div[@class="objbox"]/table/tbody',
            1, 1))
    },
    title='Cloud Tenants')


details_page = Region(infoblock_type='detail')


class Tenant(object):
    def __init__(self, name, description, provider_key):
        """Base class for a Tenant"""
        self.name = name
        self.description = description
        self.provider_key = provider_key

    def exists(self):
        sel.force_navigate('clouds_tenants')
        provider_name = cfme_data.get('management_systems', {})[self.provider_key]['name']
        res = list_page.tenant_table.find_row_by_cells({'Name': self.name,
                                                        'Cloud Provider': provider_name})
        if res:
            return True
        else:
            return False
