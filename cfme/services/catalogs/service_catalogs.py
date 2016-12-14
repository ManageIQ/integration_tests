# -*- coding: utf-8 -*-
from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import (accordion, flash, form_buttons, Form, Input, Select,
    match_location, toolbar as tb, PagedTable)
from selenium.common.exceptions import NoSuchElementException
from utils.appliance.implementations.ui import CFMENavigateStep, navigate_to, navigator
from utils.appliance import Navigatable
from utils.update import Updateable
from utils.pretty import Pretty

order_button = "//button[@title='Order this Service']"

accordion_tree = partial(accordion.tree, "Service Catalogs")
list_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")

# Forms
stack_form = Form(
    fields=[
        ('timeout', Input("stack_timeout")),
        ('key_name', Input("param_KeyName")),
        ('db_user', Input("param_DBUser__protected")),
        ('db_password', Input("param_DBPassword__protected")),
        ('db_root_password', Input("param_DBRootPassword__protected")),
        ('select_instance_type', Select("//select[@id='param_InstanceType']")),
        ('stack_name', Input("stack_name")),
        ('resource_group', Select("//select[@id='resource_group']")),
        ('mode', Select("//select[@id='deploy_mode']")),
        ('vm_name', Input("param_virtualMachineName")),
        ('vm_user', Input("param_adminUserName")),
        ('vm_password', Input("param_adminPassword__protected")),
        ('vm_size', Select("//select[@id='param_virtualMachineSize']"))
    ])

dialog_form = Form(
    fields=[
        ('default_select_value', Select("//select[@id='service_level']"))
    ])

match_page = partial(match_location, title='Catalogs', controller='catalog')


class ServiceCatalogs(Updateable, Pretty, Navigatable):
    pretty_attrs = ['service_name']

    def __init__(self, service_name=None, stack_data=None, dialog_values=None, appliance=None):
        self.service_name = service_name
        self.stack_data = stack_data
        self.dialog_values = dialog_values
        Navigatable.__init__(self, appliance=appliance)

    def order(self):
        navigate_to(self, 'Order')
        if self.stack_data:
            stack_form.fill(self.stack_data)
        if self.dialog_values:
            dialog_form.fill(self.dialog_values)
        sel.click(form_buttons.submit)
        # TO DO - needs to be reworked and remove sleep
        sel.sleep(5)
        flash.assert_success_message("Order Request was Submitted")


@navigator.register(ServiceCatalogs, 'All')
class ServiceCatalogsAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='All Services')

    def step(self):
        self.prerequisite_view.navigation.select('Services', 'Catalogs')
        tree = accordion.tree('Service Catalogs')
        tree.click_path('All Services')


@navigator.register(ServiceCatalogs, 'Details')
class ServiceCatalogDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='Service "{}"'.format(self.obj.service_name))

    def step(self):
        try:
            sel.click(list_tbl.find_row_by_cell_on_all_pages({'Name': self.obj.service_name}))
        except:
            raise NoSuchElementException()

    def resetter(self):
        tb.refresh()


@navigator.register(ServiceCatalogs, 'Order')
class ServiceCatalogOrder(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return match_page(summary='Order Service "{}"'.format(self.obj.service_name))

    def step(self):
        sel.click(order_button)
