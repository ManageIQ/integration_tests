# -*- coding: utf-8 -*-
from collections import Mapping
from copy import copy
from functools import partial

from cached_property import cached_property

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.utils import ParametrizedLocator, ParametrizedString
from widgetastic.widget import Text, ParametrizedView
from widgetastic_manageiq import Select
from widgetastic_patternfly import Input, Button, Dropdown

from cfme.base.login import BaseLoggedInPage
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.accordion as accordion
from cfme.web_ui import Form, Tree, fill, flash, form_buttons, match_location, Select as Select_old
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from utils.pretty import Pretty
from utils.update import Updateable
from utils.version import LOWEST, pick


assignment_tree = Tree("//div[@id='cb_assignments_treebox']/ul")


match_page = partial(match_location, controller='chargeback',
                     title='Chargeback')


class ChargebackView(BaseLoggedInPage):
    @property
    def in_chargeback(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Cloud Intel', 'Chargeback'])

    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == 'Compute Chargeback Rates')

    configuration = Dropdown('Configuration')


class AddComputeChargebackView(ChargebackView):
    title = Text('#explorer_title_text')

    description = Input(id='description')
    currency = Select(id='currency')

    @ParametrizedView.nested
    class fields(ParametrizedView):  # noqa
        PARAMETERS = ('name',)
        ROOT = ParametrizedLocator('.//tr[./td[contains(normalize-space(.), {name|quote})]]')

        @cached_property
        def row_id(self):
            attr = self.browser.get_attribute(
                'id',
                './td/select[starts-with(@id, "per_time_")]',
                parent=self)
            return int(attr.rsplit('_', 1)[-1])

        @cached_property
        def sub_row_id(self):
            attr = self.browser.get_attribute(
                'id',
                './td/input[starts-with(@id, "fixed_rate_")]',
                parent=self)
            return int(attr.rsplit('_', 1)[-1])

        per_time = Select(id=ParametrizedString('per_time_{@row_id}'))
        per_unit = Select(id=ParametrizedString('per_unit_{@row_id}'))
        start = Input(id=ParametrizedString('start_{@row_id}_{@sub_row_id}'))
        finish = Input(id=ParametrizedString('finish_{@row_id}_{@sub_row_id}'))
        fixed_rate = Input(id=ParametrizedString('fixed_rate_{@row_id}_{@sub_row_id}'))
        variable_rate = Input(id=ParametrizedString('variable_rate_{@row_id}_{@sub_row_id}'))
        action_add = Button(title='Add a new tier')
        action_delete = Button(title='Remove the tier')

    add_button = Button(title='Add')
    cancel_button = Button(title='Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Compute Chargeback Rates' and
            self.description.is_displayed)


class EditComputeChargebackView(AddComputeChargebackView):

    save_button = Button(title='Save Changes')
    reset_button = Button(title='Reset Changes')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Compute Chargeback Rate "{}"'.format(self.obj.description))


class StorageChargebackView(ChargebackView):
    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == 'Storage Chargeback Rates')


class AddStorageChargebackView(AddComputeChargebackView):
    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Storage Chargeback Rates' and
            self.description.is_displayed)


class EditStorageChargebackView(EditComputeChargebackView):
    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Storage Chargeback Rate "{}"'.format(self.obj.description))


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
        el = pick({"5.6": "./td/select",
                   "5.7": "./td/div/select"})
        return Select_old(sel.element(el, root=row))

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
        ("assign_to", Select_old("select#cbshow_typ")),
        # Enterprise
        ("enterprise", Select_old("select#enterprise__1")),  # Simple shotcut, might explode once
        # Tagged DS
        ("tag_category", Select_old("select#cbtag_cat")),
        # Docker Labels
        ("docker_labels", Select_old('select#cblabel_key')),
        # Common - selection table
        ("selections", AssignFormTable({
            LOWEST: (
                "//div[@id='cb_assignment_div']/fieldset/table[contains(@class, 'style1')]"
                "/tbody/tr/td/table"),
            "5.4": "//div[@id='cb_assignment_div']/table[contains(@class, 'table')]",
        })),
        ('save_button', form_buttons.save)])


class ComputeRate(Updateable, Pretty, Navigatable):
    pretty_attrs = ['description']

    def __init__(self, description=None,
                 currency=None,
                 fields=None,
                 appliance=None,
                 ):
        Navigatable.__init__(self, appliance=appliance)
        self.description = description
        self.currency = currency
        self.fields = fields

    def __getitem__(self, name):
        return self.fields.get(name, None)

    def create(self):
        view = navigate_to(self, 'New')
        view.fill_with({'description': self.description,
                        'currency': self.currency,
                        'fields': self.fields},
                       on_change=view.add_button,
                       no_change=view.cancel_button)

        view.flash.assert_success_message('Chargeback Rate "{}" was added'.format(
            self.description))

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        view.fill_with(updates, on_change=view.save_button, no_change=view.cancel_button)
        view.flash.assert_success_message('Chargeback Rate "{}" was saved'.format(
            updates.get('description')))

    def delete(self):
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Remove from the VMDB', handle_alert=True)
        view.flash.assert_success_message('Chargeback Rate "{}": Delete successful'.format(
            self.description))


@navigator.register(ComputeRate, 'All')
class ComputeRateAll(CFMENavigateStep):
    VIEW = ChargebackView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Cloud Intel', 'Chargeback')
        accordion.tree("Rates", "Rates", "Compute")


@navigator.register(ComputeRate, 'New')
class ComputeRateNew(CFMENavigateStep):
    VIEW = AddComputeChargebackView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.view.configuration.item_select("Add a new Chargeback Rate")


@navigator.register(ComputeRate, 'Details')
class ComputeRateDetails(CFMENavigateStep):
    VIEW = ChargebackView
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Rates", "Rates", "Compute", self.obj.description)


@navigator.register(ComputeRate, 'Edit')
class ComputeRateEdit(CFMENavigateStep):
    VIEW = EditComputeChargebackView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.configuration.item_select("Edit this Chargeback Rate")


class StorageRate(ComputeRate, Updateable, Pretty, Navigatable):
    # Identical methods and form with ComputeRate but different navigation
    pretty_attrs = ['description']


@navigator.register(StorageRate, 'All')
class StorageRateAll(CFMENavigateStep):
    VIEW = StorageChargebackView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Cloud Intel', 'Chargeback')
        accordion.tree("Rates", "Rates", "Storage")


@navigator.register(StorageRate, 'New')
class StorageRateNew(CFMENavigateStep):
    VIEW = AddStorageChargebackView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.view.configuration.item_select("Add a new Chargeback Rate")


@navigator.register(StorageRate, 'Details')
class StorageRateDetails(CFMENavigateStep):
    VIEW = ChargebackView
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Rates", "Rates", "Storage", self.obj.description)


@navigator.register(StorageRate, 'Edit')
class StorageRateEdit(CFMENavigateStep):
    VIEW = EditStorageChargebackView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.configuration.item_select("Edit this Chargeback Rate")


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
                 docker_labels=None,
                 selections=None,
                 appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.assign_to = assign_to
        self.tag_category = tag_category
        self.docker_labels = docker_labels
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
             'docker_labels': self.docker_labels,
             'selections': self.selections},
            action=assign_form.save_button)
        flash.assert_no_errors()


@navigator.register(Assign, 'All')
class AssignAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Cloud Intel', 'Chargeback')
        accordion.tree("Rates", "Rates", "Storage")


@navigator.register(Assign, 'Storage')
class AssignStorage(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Assignments", "Assignments", "Storage")

    def am_i_here(self):
        return match_page(summary='Storage Rate Assignments')


@navigator.register(Assign, 'Compute')
class AssignCompute(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Assignments", "Assignments", "Compute")

    def am_i_here(self):
        return match_page(summary='Compute Rate Assignments')
