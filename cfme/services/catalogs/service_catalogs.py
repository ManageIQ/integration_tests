# -*- coding: utf-8 -*-
from functools import partial

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import accordion, flash, menu, form_buttons
from utils.update import Updateable
from utils.pretty import Pretty
from utils import version

order_button = {
    version.LOWEST: "//img[@title='Order this Service']",
    '5.4': "//button[@title='Order this Service']"
}
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
                           context={'catalog': catalog,
                                    'catalog_item': catalog_item})
        sel.click(form_buttons.submit)
        flash.assert_success_message("Order Request was Submitted")
