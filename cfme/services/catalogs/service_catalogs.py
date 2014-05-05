import ui_navigate as nav
from cfme.web_ui import Form, accordion, fill
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui as web_ui
from utils.update import Updateable

order_button = "//img[@title='Order this Service']"
service_catalog_tree = web_ui.Tree('//div[@id="sandt_tree_box"]//table')

service_order_form = Form(
    fields=[('dialog_service_name_field', "//tr/td[@title='ele_desc']/input[@id='service_name']"),
            ('submit_button', "//img[@title='Submit']")])


nav.add_branch(
    'services_catalogs',
    {'service_catalogs': [nav.partial(accordion.click, 'Service Catalogs'),
        {'service_catalog': [lambda ctx: service_catalog_tree.click_path('All Services',
        ctx['catalog'], ctx['catalog_item'].name),
            {'order_service_catalog': nav.partial(sel.click, order_button)}]}]})


class ServiceCatalogs(Updateable):

    def __init__(self, service_name=None):
        self.service_name = service_name

    def order(self, catalog, catalog_item):
        sel.force_navigate('order_service_catalog',
            context={'catalog': catalog, 'catalog_item': catalog_item})
        fill(service_order_form, {'dialog_service_name_field': self.service_name},
            action=service_order_form.submit_button)
