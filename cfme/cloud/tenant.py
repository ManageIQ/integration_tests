""" Page functions for Tenant pages


:var list_page: A :py:class:`cfme.web_ui.Region` object describing elements on the list page.
:var details_page: A :py:class:`cfme.web_ui.Region` object describing elements on the detail page.
"""
from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute
from selenium.common.exceptions import NoSuchElementException

from cfme.exceptions import TenantNotFound, DestinationNotFound, OptionNotAvailable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    PagedTable, CheckboxTable, toolbar as tb, match_location, Form, AngularSelect, Input,
    form_buttons, flash, paginator)
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from utils.log import logger
from utils.version import current_version
from utils.wait import wait_for, TimedOutError

create_tenant_form = Form(
    fields=[
        ('prov_select', AngularSelect("ems_id")),
        ('name', Input('name')),
        ('save_button', form_buttons.angular_save),
        ('reset_button', form_buttons.reset)
    ])

listview_pagetable = PagedTable(table_locator="//div[@id='list_grid']//table")
listview_checktable = CheckboxTable(table_locator="//div[@id='list_grid']//table")

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')

match_page = partial(match_location, controller='cloud_tenant', title='Cloud Tenants')


class Tenant(Navigatable):
    def __init__(self, name, provider, appliance=None):
        """Base class for a Tenant"""
        self.name = name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    def create(self, cancel=False):
        navigate_to(self, 'Add')
        create_tenant_form.fill(
            {'prov_select': self.provider.name,
             'name': self.name})
        sel.click(form_buttons.cancel if cancel else create_tenant_form.save_button)

        if cancel:
            return flash.assert_success_message('Add of new Cloud Tenant was cancelled by the user')
        else:
            return flash.assert_success_message('Cloud Tenant "{}" created'.format(self.name))

    def wait_for_disappear(self, timeout=300):
        try:
            return wait_for(self.exists,
                            fail_condition=True,
                            timeout=timeout,
                            message='Wait for cloud tenant to disappear',
                            delay=10,
                            fail_func=sel.refresh)
        except TimedOutError:
            logger.error('Timed out waiting for tenant to disappear, continuing')

    def delete(self, cancel=False, from_details=True, wait=True):
        if current_version() < '5.7':
            raise OptionNotAvailable('Cannot delete cloud tenants in CFME < 5.7')
        if from_details:
            if cancel:
                raise OptionNotAvailable('Cannot cancel cloud tenant delete from details page')
            # Generates no alert or confirmation
            try:
                navigate_to(self, 'Details')
            except Exception as ex:
                # Catch general navigation exceptions and raise
                raise TenantNotFound('Exception while navigating to Tenant details: {}'
                                     .format(ex))
            cfg_btn('Delete Cloud Tenant')
        else:
            # Have to select the row in the list
            navigate_to(self, 'All')
            # double check we're in List View
            tb.select('List View')
            found = False
            for page in paginator.pages():
                try:
                    listview_checktable.select_row_by_cells(
                        {'Name': self.name,
                         'Cloud Provider': self.provider.name})
                    found = True
                except NoSuchElementException:
                    continue
                else:
                    break
            if not found:
                raise TenantNotFound('Could not locate tenant for delete by selection')
            cfg_btn('Delete Cloud Tenants', invokes_alert=True)
            sel.handle_alert(cancel=cancel)

        if cancel:
            return self.exists()
        else:
            # Flash message is the same whether deleted from details or by selection
            result = flash.assert_success_message('Delete initiated for 1 Cloud Tenant.')
            if wait:
                result = self.wait_for_disappear()
            return result

    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except Exception:
            return False


@navigator.register(Tenant, 'All')
class TenantAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='Cloud Tenants')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Tenants')


@navigator.register(Tenant, 'Details')
class TenantDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self, *args, **kwargs):
        sel.click(listview_pagetable.find_row_by_cell_on_all_pages(
            {'Name': self.obj.name,
             'Cloud Provider': self.obj.provider.name}))

    def resetter(self):
        sel.refresh()


@navigator.register(Tenant, 'Add')
class TenantAdd(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        if current_version() >= '5.7':
            cfg_btn('Create Cloud Tenant')
        else:
            raise DestinationNotFound('Cannot add Cloud Tenants in CFME < 5.7')


@navigator.register(Tenant, 'Edit')
class TenantEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        if current_version() >= '5.7':
            cfg_btn('Edit Cloud Tenant')
        else:
            raise DestinationNotFound('Cannot edit Cloud Tenants in CFME < 5.7')


@navigator.register(Tenant, 'EditTags')
class TenantEditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        pol_btn('Edit Tags')
