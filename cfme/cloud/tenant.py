""" Page functions for Tenant pages


:var list_page: A :py:class:`cfme.web_ui.Region` object describing elements on the list page.
:var details_page: A :py:class:`cfme.web_ui.Region` object describing elements on the detail page.
"""

from utils.conf import cfme_data
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Region, SplitTable, toolbar as tb, CheckboxTable, Form, form_buttons
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from navmazing import NavigateToAttribute, NavigateToSibling
from cfme.cloud.instance import match_page
from cfme.common import SummaryMixin, Taggable

# Page specific locators
list_page = Region(
    locators={
        'tenant_table': SplitTable(header_data=('//div[@class="xhdr"]/table/tbody', 1),
                                   body_data=('//div[@class="objbox"]/table/tbody', 1))
    },
    title='Cloud Tenants')

create_form = Form([('cloud_provider', ("//button[@id='cloud_tenant_id']"),
                     ('tenant_name', "//*[@name='name']"))])
list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
details_page = Region(infoblock_type='detail')


class Tenant(Taggable, SummaryMixin, Navigatable):
    def __init__(self, name, description, provider_key):
        """Base class for a Tenant"""
        self.name = name
        self.description = description
        self.provider_key = provider_key
        Navigatable.__init__(self)

    def create(self, provider_key):
        """
            create a new tenant
        """
        navigate_to(Tenant, 'All')
        tb.select('Configuration', 'Create Cloud Tenant')
        tenant_data = dict(tenant_name=self.name, provider_name=provider_key)
        create_form.fill(tenant_data)
        sel.click(form_buttons.save)

    def update(self, tenant_name, new_name):
        """
            update a given cloud tenant name to new tenant
        """
        navigate_to(Tenant, 'All')
        list_tbl.select_row('Name', tenant_name)
        tb.select('Configuration', 'Edit Selected Cloud Tenant')
        tenant_data = dict(tenant_name=new_name)
        create_form.fill(tenant_data)
        sel.click(form_buttons.save)

    def delete(self, tenant_name):
        navigate_to(Tenant, 'All')
        list_tbl.select_row('Name', tenant_name)
        tb.select('Configuration', 'Delete Cloud Tenants', invokes_alert=True)
        sel.handle_alert()

    def exists(self):
        sel.force_navigate('clouds_tenants')
        provider_name = cfme_data.get('management_systems', {})[self.provider_key]['name']
        res = list_page.tenant_table.find_row_by_cells({'Name': self.name,
                                                        'Cloud Provider': provider_name})
        if res:
            return True
        else:
            return False

    def click_element(self, *ident):
        self.load_details(refresh=True)
        return sel.click(details_page.infoblock.element(*ident))

    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        if refresh:
            tb.refresh()


@navigator.register(Tenant, 'All')
class TenantAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='Cloud Tenants')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Clouds', 'Tenants')(None)

    def resetter(self):
        tb.select('List View')


@navigator.register(Tenant, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        tb.select('List View')
        list_tbl.click_row_by_cells({'Name': self.obj.name})
