# -*- coding: utf-8 -*-
from functools import partial

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Form, accordion, fill, flash, menu
from utils.update import Updateable
from utils.pretty import Pretty

order_button = "//img[@title='Order this Service']"

service_order_form = Form(
    fields=[('dialog_service_name_field', "//tr/td[@title='ele_desc']/input[@id='service_name']"),
            ('submit_button', "//img[@title='Submit']")])

accordion_tree = partial(accordion.tree, "Service Catalogs")

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

    def __init__(self, service_name=None):
        self.service_name = service_name

    def order(self, catalog, catalog_item):
        sel.force_navigate('order_service_catalog',
            context={'catalog': catalog, 'catalog_item': catalog_item})
        fill(service_order_form, {'dialog_service_name_field': self.service_name},
            action=service_order_form.submit_button)
        flash.assert_success_message("Order Request was Submitted")
