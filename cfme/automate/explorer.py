from functools import partial

import ui_navigate as nav

import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.menu  # so that menu is already loaded before grafting onto it
import cfme.web_ui.toolbar as tb
from cfme.web_ui import Form, SplitTable, Tree, fill
from utils.log import logger
from utils.update import Updateable

root_data_table = SplitTable(
    header_data=('//div[@id="ns_list_grid_div"]/div[@class="xhdr"]/table/tbody', 1),
    body_data=('//div[@id="ns_list_grid_div"]/div[@class="objbox"]/table/tbody', 1)
)

sub_data_table = SplitTable(
    header_data=('//div[@id="ns_grid_div"]/div[@class="xhdr"]/table/tbody', 1),
    body_data=('//div[@id="ns_grid_div"]/div[@class="objbox"]/table/tbody', 1)
)

tree = Tree('//table//tr[@title="Datastore"]/../..')

cfg_btn = partial(tb.select, 'Configuration')

nav.add_branch('automate_explorer',
               {
                   'automate_explorer_add_ns': lambda ctx: add_namespace(ctx),
                   'automate_explorer_edit_ns': lambda ctx: edit_namespace(ctx),
               })


class Namespace(Updateable):
    namespace_form = Form(
        fields=[
            ('ns_name', "//*[@id='ns_name']"),
            ('ns_description', "//*[@id='ns_description']"),
            ('ns_add_btn', "//ul[@id='form_buttons']/li/img[@alt='Add']"),
            ('ns_save_btn', "//ul[@id='form_buttons']/li/img[@alt='Save Changes']"),
            ('ns_cancel_btn', "//ul[@id='form_buttons']/li/img[@alt='Cancel']"),
        ])

    create_btn_map = {True: namespace_form.ns_cancel_btn, False: namespace_form.ns_add_btn}
    update_btn_map = {True: namespace_form.ns_cancel_btn, False: namespace_form.ns_save_btn}

    def __init__(self, name=None, description=None, path=None):
        self.name = name
        self.description = description
        self.path = path

    def create(self, cancel=False):
        sel.force_navigate('automate_explorer_add_ns', context=self)
        form_data = {'ns_name': self.name,
                     'ns_description': self.description}
        fill(self.namespace_form, form_data, action=self.create_btn_map[cancel])

    def update(self, updates, cancel=False):
        sel.force_navigate('automate_explorer_edit_ns', context=self)
        form_data = {'ns_name': updates.get('name') or None,
                     'ns_description': updates.get('description') or None}
        fill(self.namespace_form, form_data, action=self.update_btn_map[cancel])

    def delete(self, cancel=True):
        delete_namespace(self, cancel=cancel)


def add_namespace(ns):
    if ns.path:
        logger.debug('Navigating the path')
        tree.click_path(*ns.path)
    else:
        sel.force_navigate('automate_explorer')
    cfg_btn('Add a New Namespace')


def select_namespace(ns):
    sel.force_navigate('automate_explorer')
    logger.debug(ns.path)
    if ns.path:
        logger.debug('Navigating the path')
        tree.click_path(*ns.path)
        sel.click(sub_data_table.find_row_by_cells({2: ns.name})[0])
    else:
        logger.debug('No need')
        sel.click(root_data_table.find_row_by_cells({'name': ns.name})[0])


def edit_namespace(ns):
    select_namespace(ns)
    if ns.path:
        cfg_btn('Edit Selected Item')
    else:
        cfg_btn('Edit Selected Namespaces')


def delete_namespace(ns, cancel=True):
    select_namespace(ns)
    if ns.path:
        cfg_btn('Remove selected Items', invokes_alert=True)
    else:
        cfg_btn('Remove Namespaces', invokes_alert=True)
    sel.handle_alert(cancel)
