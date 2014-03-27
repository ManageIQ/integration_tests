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
        ('description', (By.CSS_SELECTOR, "input#description")),
        # Compute form items
        ('cpu_alloc', _mkitem(0)),
        ('cpu_used', _mkitem(1)),
        ('disk_io', _mkitem(2)),
        ('compute_fixed_1', _mkitem(3)),
        ('compute_fixed_2', _mkitem(4)),
        ('mem_alloc', _mkitem(5)),
        ('mem_used', _mkitem(6)),
        ('net_io', _mkitem(7)),
        # Storage form items
        ('storage_fixed_1', _mkitem(0)),
        ('storage_fixed_2', _mkitem(1)),
        ('storage_alloc', _mkitem(2)),
        ('storage_used', _mkitem(3)),
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
    fill(rf.unit_select_loc, sel.ByValue(value[1]))


class ComputeRate(Updateable):
    def __init__(self, description=None,
                 cpu_alloc=None,
                 cpu_used=None,
                 disk_io=None,
                 compute_fixed_1=None,
                 compute_fixed_2=None,
                 mem_alloc=None,
                 mem_used=None,
                 net_io=None
                 ):
        self.description = description
        self.cpu_alloc = cpu_alloc
        self.cpu_used = cpu_used
        self.disk_io = disk_io
        self.compute_fixed_1 = compute_fixed_1
        self.compute_fixed_2 = compute_fixed_2
        self.mem_alloc = mem_alloc
        self.mem_used = mem_used
        self.net_io = net_io

    def create(self):
        sel.force_navigate('chargeback_rates_compute_new')
        fill(rate_form,
            {'description': self.description,
             'cpu_alloc': self.cpu_alloc,
             'cpu_used': self.cpu_used,
             'disk_io': self.disk_io,
             'compute_fixed_1': self.compute_fixed_1,
             'compute_fixed_2': self.compute_fixed_2,
             'mem_alloc': self.mem_alloc,
             'mem_used': self.mem_used,
             'net_io': self.net_io},
            action=rate_form.add_button)
        flash.assert_no_errors()

    def update(self, updates):
        sel.force_navigate('chargeback_rates_compute_edit', context={'chargeback': self})
        fill(rate_form,
            {'description': updates.get('description'),
             'cpu_alloc': updates.get('cpu_alloc'),
             'cpu_used': updates.get('cpu_used'),
             'disk_io': updates.get('disk_io'),
             'compute_fixed_1': updates.get('compute_fixed_1'),
             'compute_fixed_2': updates.get('compute_fixed_2'),
             'mem_alloc': updates.get('memory_allocated'),
             'mem_used': updates.get('memory_used'),
             'net_io': updates.get('network_io')},
            action=rate_form.save_button)
        flash.assert_no_errors()

    def delete(self):
        sel.force_navigate('chargeback_rates_compute_named', context={'chargeback': self})
        tb_select('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()


class StorageRate(Updateable):
    def __init__(self, description=None,
                 storage_fixed_1=None,
                 storage_fixed_2=None,
                 storage_alloc=None,
                 storage_used=None):
        self.description = description
        self.storage_fixed_1 = storage_fixed_1
        self.storage_fixed_2 = storage_fixed_2
        self.storage_alloc = storage_alloc
        self.storage_used = storage_used

    def create(self):
        sel.force_navigate('chargeback_rates_storage_new')
        fill(rate_form,
            {'description': self.description,
             'storage_fixed_1': self.storage_fixed_1,
             'storage_fixed_2': self.storage_fixed_2,
             'storage_alloc': self.storage_alloc,
             'storage_used': self.storage_used},
            action=rate_form.add_button)

    def update(self, updates):
        sel.force_navigate('chargeback_rates_storage_edit', context={'chargeback': self})
        fill(rate_form,
            {'description': updates.get('description'),
             'storage_fixed_1': updates.get('storage_fixed_1'),
             'storage_fixed_2': updates.get('storage_fixed_2'),
             'storage_alloc': updates.get('storage_alloc'),
             'storage_used': updates.get('storage_used')},
            action=rate_form.save_button)

    def delete(self):
        sel.force_navigate('chargeback_rates_storage_named', context={'chargeback': self})
        tb_select('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()
