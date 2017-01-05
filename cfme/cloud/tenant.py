""" Page functions for Tenant pages


:var list_page: A :py:class:`cfme.web_ui.Region` object describing elements on the list page.
:var details_page: A :py:class:`cfme.web_ui.Region` object describing elements on the detail page.
"""
from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute
from selenium.common.exceptions import NoSuchElementException

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import PagedTable, toolbar as tb, match_location
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to

listview_table = PagedTable(table_locator="//div[@id='list_grid']//table")

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')

match_page = partial(match_location, controller='cloud_tenant', title='Cloud Tenants')


class Tenant(Navigatable):
    def __init__(self, name, description, provider, appliance=None):
        """Base class for a Tenant"""
        self.name = name
        self.description = description
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except NoSuchElementException:
            return False


@navigator.register(Tenant, 'All')
class TenantAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='Cloud Tenants')

    def step(self, *args, **kwargs):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Clouds', 'Tenants')(None)


@navigator.register(Tenant, 'Details')
class TenantDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self, *args, **kwargs):
        sel.click(listview_table.find_row_by_cell_on_all_pages(
            {'Name': self.obj.name,
             'Cloud Provider': self.obj.provider.name}))

    def resetter(self):
        tb.refresh()


@navigator.register(Tenant, 'Add')
class TenantAdd(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        cfg_btn('Create Cloud Tenant')


@navigator.register(Tenant, 'Edit')
class TenantEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        cfg_btn('Edit Tenant')


@navigator.register(Tenant, 'EditTags')
class TenantEditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        pol_btn('Edit Tags')
