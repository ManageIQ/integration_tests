# -*- coding: utf-8 -*-
from functools import partial

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import accordion, fill, flash, menu, form_buttons, Form, Input, Select
from utils.update import Updateable
from utils.pretty import Pretty
from utils import version

order_button = {
    version.LOWEST: "//img[@title='Order this Service']",
    '5.4': "//button[@title='Order this Service']"
}
accordion_tree = partial(accordion.tree, "Service Catalogs")

# Forms
stack_form = Form(
    fields=[
        ('timeout', Input("stack_timeout")),
        ('key_name', Input("param_KeyName")),
        ('db_user', Input("param_DBUser__protected")),
        ('db_password', Input("param_DBPassword__protected")),
        ('db_root_password', Input("param_DBRootPassword__protected")),
        ('select_instance_type', Select("//select[@id='param_InstanceType']")),
        ('stack_name', Input("stack_name"))
    ])


menu.nav.add_branch(
    'services_catalogs',
    {
        'service_catalogs':
        [
            lambda _: accordion.click('Service Catalogs'),
            {
                'service_catalog':
                [
                    lambda ctx: accordion_tree(
                        'All Services', ctx['catalog'], ctx['catalog_item'].name),
                    {
                        'order_service_catalog': lambda _: sel.click(order_button)
                    }
                ]
            }
        ]
    }
)


class ServiceCatalogs(Updateable, Pretty):
    pretty_attrs = ['service_name']

    def __init__(self, service_name=None, stack_data=None):
        self.service_name = service_name
        self.stack_data = stack_data

    def order(self, catalog, catalog_item):
        sel.force_navigate('order_service_catalog',
                           context={'catalog': catalog,
                                    'catalog_item': catalog_item})
        sel.click(form_buttons.submit)
        flash.assert_success_message("Order Request was Submitted")

    def order_stack_item(self, catalog, catalog_item):
        sel.force_navigate('order_service_catalog',
                           context={'catalog': catalog,
                                    'catalog_item': catalog_item})
        stack_form.fill(self.stack_data)
        sel.click(form_buttons.submit)
        flash.assert_success_message("Order Request was Submitted")


def order_catalog_item(catalog_item, data={}):  # {} won't get mutated here
    sel.force_navigate(
        "order_service_catalog",
        context={"catalog": catalog_item.catalog, "catalog_item": catalog_item})
    for loc, val in data.iteritems():
        fill(loc, val)
    sel.click(form_buttons.submit)
    flash.assert_message_match("Order Request was Submitted")
    flash.assert_no_errors()
