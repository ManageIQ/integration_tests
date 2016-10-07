# -*- coding: utf-8 -*-
from collections import Mapping
from copy import copy
from functools import partial

from selenium.webdriver.common.by import By
from navmazing import NavigateToSibling, NavigateToAttribute
import cfme.web_ui.accordion as accordion
import cfme.web_ui.toolbar as tb
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Form, Select, Tree, fill, flash, form_buttons, summary_title
from utils.pretty import Pretty
from utils.update import Updateable
from utils.version import LOWEST
from utils.appliance import Navigatable
from utils.appliance.endpoints.ui import navigator, navigate_to, CFMENavigateStep

assignment_tree = Tree("//div[@id='cb_assignments_treebox']/ul")
tb_select = partial(tb.select, "Configuration")


class RateFormItem(Pretty):
    pretty_attrs = ['rate_loc', 'unit_select_loc']

    def __init__(self, rate_loc=None, unit_select_loc=None):
        self.rate_loc = rate_loc
        self.unit_select_loc = unit_select_loc


def _mkitem(field, index1, index2=0):
    return RateFormItem((By.CSS_SELECTOR, "input#{}_{}_{}".format(field, index1, index2)),
                        Select((By.CSS_SELECTOR, "select#per_time_" + str(index1))))

rate_form = Form(
    fields=[
        ('description', (By.CSS_SELECTOR, "input#description")),
        # Compute form items fixed
        ('cpu_alloc', _mkitem("fixed_rate", 0)),
        ('cpu_used', _mkitem("fixed_rate", 1)),
        ('cpu_cores_used', _mkitem("fixed_rate", 2)),
        ('disk_io', _mkitem("fixed_rate", 3)),
        ('compute_fixed_1', _mkitem("fixed_rate", 4)),
        ('compute_fixed_2', _mkitem("fixed_rate", 5)),
        ('mem_alloc', _mkitem("fixed_rate", 6)),
        ('mem_used', _mkitem("fixed_rate", 7)),
        ('net_io', _mkitem("fixed_rate", 8)),
        ('net_io_2', _mkitem("fixed_rate", 8, 1)),
        # Compute form items variable
        ('cpu_alloc_var', _mkitem("variable_rate", 0)),
        ('cpu_used_var', _mkitem("variable_rate", 1)),
        ('cpu_cores_used_var', _mkitem("variable_rate", 2)),
        ('disk_io_var', _mkitem("variable_rate", 3)),
        ('compute_fixed_1_var', _mkitem("variable_rate", 4)),
        ('compute_fixed_2_var', _mkitem("variable_rate", 5)),
        ('mem_alloc_var', _mkitem("variable_rate", 6)),
        ('mem_used_var', _mkitem("variable_rate", 7)),
        ('net_io_var', _mkitem("variable_rate", 8)),
        ('net_io_2_var', _mkitem("variable_rate", 8, 1)),
        # Storage form items
        ('storage_fixed_1', _mkitem("fixed_rate", 0)),
        ('storage_fixed_2', _mkitem("fixed_rate", 1)),
        ('storage_alloc', _mkitem("fixed_rate", 2)),
        ('storage_used', _mkitem("fixed_rate", 3)),
        # Storage form items variable
        ('storage_fixed_1_var', _mkitem("variable_rate", 0)),
        ('storage_fixed_2_var', _mkitem("variable_rate", 1)),
        ('storage_alloc_var', _mkitem("variable_rate", 2)),
        ('storage_used_var', _mkitem("variable_rate", 3)),
        ('add_button', form_buttons.add),
        ('save_button', form_buttons.save),
        ('reset_button', form_buttons.reset),
        ('cancel_button', form_buttons.cancel)])


class AssignFormTable(Pretty):
    pretty_attrs = ["entry_loc"]

    def __init__(self, entry_loc):
        self.entry_loc = entry_loc

    def locate(self):
        return self.entry_loc

    @property
    def rows(self):
        return sel.elements("./tbody/tr", root=self)

    def row_by_name(self, name):
        for row in self.rows:
            row_name = sel.text_sane(sel.element("./td[1]", root=row))
            if row_name == name:
                return row
        else:
            raise NameError("Did not find row named {}!".format(name))

    def select_from_row(self, row):
        return Select(sel.element("./td/select", root=row))

    def select_by_name(self, name):
        return self.select_from_row(self.row_by_name(name))


@fill.method((AssignFormTable, Mapping))
def _fill_assignform_dict(form, d):
    d = copy(d)  # Mutable
    for name, value in d.iteritems():
        if value is None:
            value = "<Nothing>"
        select = form.select_by_name(name)
        sel.select(select, value)


assign_form = Form(
    fields=[
        ("assign_to", Select("select#cbshow_typ")),
        # Enterprise
        ("enterprise", Select("select#enterprise__1")),  # Simple shotcut, might explode one time
        # Tagged DS
        ("tag_category", Select("select#cbtag_cat")),
        # Common - selection table
        ("selections", AssignFormTable({
            LOWEST: (
                "//div[@id='cb_assignment_div']/fieldset/table[contains(@class, 'style1')]"
                "/tbody/tr/td/table"),
            "5.4": "//div[@id='cb_assignment_div']/table[contains(@class, 'table')]",
        })),
        ('save_button', form_buttons.save)])


HOURLY = 'hourly'
DAILY = 'daily'
WEEKLY = 'weekly'
MONTHLY = 'monthly'


@fill.method((RateFormItem, tuple))
def _fill_rateform(rf, value):
    """value should be like (5, HOURLY)"""
    fill(rf.rate_loc, value[0])
    fill(rf.unit_select_loc, sel.ByValue(value[1]))


@fill.method((RateFormItem))
def _fill_assignform(rf, value):
    fill(rf.rate_loc, value)


class ComputeRate(Updateable, Pretty, Navigatable):
    pretty_attrs = ['description']

    def __init__(self, description=None,
                 cpu_alloc=None,
                 cpu_used=None,
                 disk_io=None,
                 compute_fixed_1=None,
                 compute_fixed_2=None,
                 mem_alloc=None,
                 mem_used=None,
                 net_io=None,
                 appliance=None):
        Navigatable.__init__(self, appliance=appliance)
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
        navigate_to(self, 'New')
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
        navigate_to(self, 'Edit')
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
        navigate_to(self, 'Details')
        tb_select('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()


@navigator.register(ComputeRate, 'All')
class ComputeRateAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Cloud Intel', 'Chargeback')(None)
        accordion.tree("Rates", "Rates", "Compute")

    def am_i_here(self):
        return summary_title() == "Compute Chargeback Rates"


@navigator.register(ComputeRate, 'New')
class ComputeRateNew(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        tb_select("Add a new Chargeback Rate")


@navigator.register(ComputeRate, 'Details')
class ComputeRateDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Rates", "Rates", "Compute", self.obj.description)

    def am_i_here(self):
        return summary_title() == 'Compute Chargeback Rate "{}"'.format(self.obj.description)


@navigator.register(ComputeRate, 'Edit')
class ComputeRateEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        tb_select("Edit this Chargeback Rate")


class StorageRate(Updateable, Pretty, Navigatable):
    pretty_attrs = ['description']

    def __init__(self, description=None,
                 storage_fixed_1=None,
                 storage_fixed_2=None,
                 storage_alloc=None,
                 storage_used=None,
                 appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.description = description
        self.storage_fixed_1 = storage_fixed_1
        self.storage_fixed_2 = storage_fixed_2
        self.storage_alloc = storage_alloc
        self.storage_used = storage_used

    def create(self):
        navigate_to(self, 'New')
        fill(rate_form,
            {'description': self.description,
             'storage_fixed_1': self.storage_fixed_1,
             'storage_fixed_2': self.storage_fixed_2,
             'storage_alloc': self.storage_alloc,
             'storage_used': self.storage_used},
            action=rate_form.add_button)

    def update(self, updates):
        navigate_to(self, 'Edit')
        fill(rate_form,
            {'description': updates.get('description'),
             'storage_fixed_1': updates.get('storage_fixed_1'),
             'storage_fixed_2': updates.get('storage_fixed_2'),
             'storage_alloc': updates.get('storage_alloc'),
             'storage_used': updates.get('storage_used')},
            action=rate_form.save_button)

    def delete(self):
        navigate_to(self, 'Details')
        tb_select('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()


@navigator.register(StorageRate, 'All')
class StorageRateAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Cloud Intel', 'Chargeback')(None)
        accordion.tree("Rates", "Rates", "Storage")

    def am_i_here(self):
        return summary_title() == 'Storage Chargeback Rates'


@navigator.register(StorageRate, 'New')
class StorageRateNew(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        tb_select("Add a new Chargeback Rate")


@navigator.register(StorageRate, 'Details')
class StorageRateDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Rates", "Rates", "Storage", self.obj.description)

    def am_i_here(self):
        return summary_title() == 'Storage Chargeback Rate "{}"'.format(self.obj.description)


@navigator.register(StorageRate, 'Edit')
class StorageRateEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        tb_select("Edit this Chargeback Rate")


class Assign(Updateable, Pretty, Navigatable):
    """
    Model of Chargeback Assignment page in cfme.

    Args:
        assign_to: Assign the chargeback rate to entities such as VM,Provider,datastore or the
            Enterprise itself.
        tag_category: Tag category of the entity
        selections: Selection of a particular entity to which the rate is to be assigned.
            Eg:If the chargeback rate is to be assigned to providers,select which of the managed
            providers the rate is to be assigned.

    Usage:
        tagged_datastore = Assign(
            assign_to="Tagged Datastores",
            tag_category="Location",
            selections={
                "Chicago": "Default"
        })
    tagged_datastore.storageassign()

    """
    def __init__(self, assign_to=None,
                 tag_category=None,
                 selections=None,
                 appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.assign_to = assign_to
        self.tag_category = tag_category
        self.selections = selections

    def storageassign(self):
        navigate_to(self, 'Storage')
        fill(assign_form,
            {'assign_to': self.assign_to,
             'tag_category': self.tag_category,
             'selections': self.selections},
            action=assign_form.save_button)
        flash.assert_no_errors()

    def computeassign(self):
        navigate_to(self, 'Compute')
        fill(assign_form,
            {'assign_to': self.assign_to,
             'tag_category': self.tag_category,
             'selections': self.selections},
            action=assign_form.save_button)
        flash.assert_no_errors()


@navigator.register(Assign, 'All')
class AssignAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Cloud Intel', 'Chargeback')(None)
        accordion.tree("Rates", "Rates", "Storage")


@navigator.register(Assign, 'Storage')
class AssignStorage(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Assignments", "Assignments", "Storage")

    def am_i_here(self):
        return summary_title() == 'Storage Rate Assignments'


@navigator.register(Assign, 'Compute')
class AssignCompute(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Assignments", "Assignments", "Compute")

    def am_i_here(self):
        return summary_title() == 'Compute Rate Assignments'
