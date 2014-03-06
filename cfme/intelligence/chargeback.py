from functools import partial

from selenium.webdriver.common.by import By

import cfme.web_ui.accordion as accordion
import cfme.web_ui.toolbar as tb
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Form, Select, Tree, fill, flash
from cfme.web_ui.menu import nav
from utils.update import Updateable

rate_tree = Tree("//div[@id='cb_rates_treebox']/ul")
tb_select = partial(tb.select, "Configuration")
tb_select_new_chargeback = nav.fn(partial(tb_select, "Add a new Chargeback Rate"))
tb_select_edit_chargeback = nav.fn(partial(tb_select, "Edit this Chargeback Rate"))


class RateFormItem(object):
    def __init__(self, rate_loc=None, unit_select_loc=None):
        self.rate_loc = rate_loc
        self.unit_select_loc = unit_select_loc


def _mkitem(index):
    return RateFormItem((By.CSS_SELECTOR, "input#rate_" + str(index)),
                        Select((By.CSS_SELECTOR, "select#per_time_" + str(index))))

rate_form = Form(
    fields=[
        ('description_text', (By.CSS_SELECTOR, "input#description")),
        # Compute form items
        ('alloc_cpu', _mkitem(0)),
        ('used_cpu', _mkitem(1)),
        ('disk_io', _mkitem(2)),
        ('fixed_1', _mkitem(3)),
        ('fixed_2', _mkitem(4)),
        ('alloc_mem', _mkitem(5)),
        ('used_mem', _mkitem(6)),
        ('net_io', _mkitem(7)),
        # Storage form items
        ('fixed_storage_1', _mkitem(0)),
        ('fixed_storage_2', _mkitem(1)),
        ('alloc_storage', _mkitem(2)),
        ('used_storage', _mkitem(3)),
        ('add_button', (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Add']")),
        ('save_button', (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Save Changes']")),
        ('reset_button', (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Reset Changes']")),
        ('cancel_button', (By.CSS_SELECTOR,
                           "div#buttons_off > ul#form_buttons > li > img[title='Cancel']"))])


nav.add_branch('chargeback',
               {'chargeback_rates':
                [nav.fn(partial(accordion.click, "Rates")),
                 {'chargeback_rates_compute':
                  [lambda d: rate_tree.click_path('Rates', 'Compute'),
                   {'chargeback_rates_compute_new': tb_select_new_chargeback}],
                  'chargeback_rates_compute_named':
                  [lambda d: rate_tree.click_path('Rates', 'Compute', d['chargeback'].description),
                   {'chargeback_rates_compute_edit': tb_select_edit_chargeback}],
                  'chargeback_rates_storage':
                  [lambda d: rate_tree.click_path('Rates', 'Storage'),
                   {'chargeback_rates_storage_new': tb_select_new_chargeback}],
                  'chargeback_rates_storage_named':
                  [lambda d: rate_tree.click_path('Rates', 'Storage', d['chargeback'].description),
                   {'chargeback_rates_storage_edit': tb_select_edit_chargeback}]}],
                'chargeback_assignments': nav.fn(partial(accordion.click, "Assignments"))})


HOURLY = 'hourly'
DAILY = 'daily'
WEEKLY = 'weekly'
MONTHLY = 'monthly'


@fill.method((RateFormItem, tuple))
def _fill_rateform(rf, value):
    '''value should be like (5, HOURLY)'''
    fill(rf.rate_loc, value[0])
    fill(rf.unit_select_loc, (sel.VALUE, value[1]))


class ComputeRate(Updateable):
    def __init__(self, description=None,
                 cpu_alloc=None,
                 cpu_used=None,
                 disk_io=None,
                 fixed_cost_1=None,
                 fixed_cost_2=None,
                 memory_allocated=None,
                 memory_used=None,
                 network_io=None
                 ):
        self.description = description
        self.cpu_alloc = cpu_alloc
        self.cpu_used = cpu_used
        self.disk_io = disk_io
        self.fixed_cost_1 = fixed_cost_1
        self.fixed_cost_2 = fixed_cost_2
        self.memory_allocated = memory_allocated
        self.memory_used = memory_used
        self.network_io = network_io

    def create(self):
        sel.force_navigate('chargeback_rates_compute_new')
        fill(rate_form,
            {'description_text': self.description,
             'alloc_cpu': self.cpu_alloc,
             'used_cpu': self.cpu_used,
             'disk_io': self.disk_io,
             'fixed_1': self.fixed_cost_1,
             'fixed_2': self.fixed_cost_2,
             'alloc_mem': self.memory_allocated,
             'used_mem': self.memory_used,
             'net_io': self.network_io},
            action=rate_form.add_button)
        flash.assert_no_errors()

    def update(self, updates):
        nav.go_to('chargeback_rates_compute_edit', context={'chargeback': self})
        fill(rate_form,
            {'description_text': updates.get('description'),
             'alloc_cpu': updates.get('cpu_alloc'),
             'used_cpu': updates.get('cpu_used'),
             'disk_io': updates.get('disk_io'),
             'fixed_1': updates.get('fixed_cost_1'),
             'fixed_2': updates.get('fixed_cost_2'),
             'alloc_mem': updates.get('memory_allocated'),
             'used_mem': updates.get('memory_used'),
             'net_io': updates.get('network_io')},
            action=rate_form.save_button)
        flash.assert_no_errors()

    def delete(self):
        nav.go_to('chargeback_rates_compute_named', context={'chargeback': self})
        tb_select('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()


class StorageRate(Updateable):
    def __init__(self, description=None,
                 fixed_cost_1=None,
                 fixed_cost_2=None,
                 allocated_storage=None,
                 used_storage=None):
        self.description = description
        self.fixed_cost_1 = fixed_cost_1
        self.fixed_cost_2 = fixed_cost_2
        self.allocated_storage = allocated_storage
        self.used_storage = used_storage

    def create(self):
        nav.go_to('chargeback_rates_storage_new')
        fill(rate_form,
            {'description_text': self.description,
             'fixed_storage_1': self.fixed_cost_1,
             'fixed_storage_2': self.fixed_cost_2,
             'alloc_storage': self.allocated_storage,
             'used_storage': self.used_storage},
            action=rate_form.add_button)

    def update(self, updates):
        nav.go_to('chargeback_rates_storage_edit', context={'chargeback': self})
        fill(rate_form,
            {'description_text': updates.get('description'),
             'fixed_storage_1': updates.get('fixed_cost_1'),
             'fixed_storage_2': updates.get('fixed_cost_2'),
             'alloc_storage': updates.get('allocated_storage'),
             'used_storage': updates.get('used_storage')},
            action=rate_form.save_button)

    def delete(self):
        nav.go_to('chargeback_rates_storage_named', context={'chargeback': self})
        tb_select('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()
