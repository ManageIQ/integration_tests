# -*- coding: utf-8 -*-
# Page model for Intel->Chargeback->Rates.
import attr
from cached_property import cached_property
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from wait_for import TimedOutError
from widgetastic.utils import ParametrizedLocator
from widgetastic.utils import ParametrizedString
from widgetastic.widget import ParametrizedView
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import CandidateNotFound
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import Input

from cfme.exceptions import ChargebackRateNotFound
from cfme.intelligence.chargeback import ChargebackView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils import ParamClassName
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.version import LOWEST
from cfme.utils.version import VersionPicker
from widgetastic_manageiq import Select
from widgetastic_manageiq import Table


class RatesView(ChargebackView):
    title = Text("#explorer_title_text")
    table = Table(".//div[@id='records_div' or @class='miq-data-table']/table")

    @property
    def in_rates(self):
        """Determine if in the rates part of chargeback, includes check of in_chargeback"""
        return(
            self.in_chargeback and
            self.toolbar.configuration.is_displayed and
            self.rates.is_opened)

    @property
    def is_displayed(self):
        expected_title = "{} Chargeback Rates".format(self.context['object'].RATE_TYPE)
        return (
            self.in_rates and
            self.rates.tree.currently_selected == ['Rates', self.context['object'].RATE_TYPE] and
            self.title.text == expected_title
        )

    @View.nested
    class toolbar(View):  # noqa
        configuration = Dropdown('Configuration')


class RatesDetailView(RatesView):
    # TODO add widget for rate details
    @property
    def is_displayed(self):
        return (
            self.in_rates and
            self.rates.tree.currently_selected == ['Rates',
                                                   self.context['object'].RATE_TYPE,
                                                   self.context['object'].description] and
            self.title.text == '{} Chargeback Rate "{}"'
                .format(self.context['object'].RATE_TYPE,
                        self.context['object'].description))


class AddComputeChargebackView(RatesView):
    EXPECTED_TITLE = 'Compute Chargeback Rates'
    title = Text('#explorer_title_text')

    description = Input(id='description')
    currency = VersionPicker({
        LOWEST: Select(id='currency'),
        '5.10': BootstrapSelect(id='currency')
    })

    @ParametrizedView.nested
    class fields(ParametrizedView):  # noqa
        PARAMETERS = ('name',)
        ROOT = ParametrizedLocator('.//tr[./td[contains(normalize-space(.), {name|quote})]]')

        @cached_property
        def row_id(self):
            dom_attr = self.browser.get_attribute(
                'id',
                './td/select[starts-with(@id, "per_time_")]',
                parent=self)
            return int(dom_attr.rsplit('_', 1)[-1])

        @cached_property
        def sub_row_id(self):
            dom_attr = self.browser.get_attribute(
                'id',
                './td/input[starts-with(@id, "fixed_rate_")]',
                parent=self)
            return int(dom_attr.rsplit('_', 1)[-1])

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
        result = (
            self.title.text == self.EXPECTED_TITLE and
            self.cancel_button.is_displayed and
            self.description.is_displayed and
            self.currency.is_displayed
        )
        return result


class EditComputeChargebackView(AddComputeChargebackView):

    save_button = Button('Save')
    reset_button = Button(title='Reset Changes')

    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == 'Compute Chargeback Rate "{}"'
                               .format(self.context['object'].description) and
            self.save_button.is_displayed
        )


class AddStorageChargebackView(AddComputeChargebackView):
    EXPECTED_TITLE = 'Storage Chargeback Rates'


class EditStorageChargebackView(EditComputeChargebackView):
    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == 'Storage Chargeback Rate "{}"'
                               .format(self.context['object'].description) and
            self.save_button.is_displayed
        )


@attr.s
class ComputeRate(Updateable, Pretty, BaseEntity):
    """This class represents a Compute Chargeback rate.

    Example:
        .. code-block:: python

          >>> import cfme.intelligence.chargeback.rates as rates
          >>> rate = rates.ComputeRate(description=desc,
                    fields={'Used CPU':
                            {'per_time': 'Hourly', 'variable_rate': '3'},
                            'Used Disk I/O':
                            {'per_time': 'Hourly', 'variable_rate': '2'},
                            'Used Memory':
                            {'per_time': 'Hourly', 'variable_rate': '2'}})
          >>> rate.create()
          >>> rate.delete()

    Args:
        description: Rate description
        currency: Rate currency
        fields  : Rate fields
    """

    pretty_attrs = ['description']
    _param_name = ParamClassName('description')
    RATE_TYPE = 'Compute'

    description = attr.ib()
    currency = attr.ib(default=None)
    fields = attr.ib(default=None)

    def __getitem__(self, name):
        return self.fields.get(name)

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
        except (ChargebackRateNotFound, TimedOutError):
            return False
        else:
            return True

    def copy(self, *args, **kwargs):
        new_rate = self.parent.instantiate(*args, **kwargs)
        add_view = navigate_to(self, 'Copy')
        add_view.fill_with(
            {
                'description': new_rate.description,
                'currency': new_rate.currency,
                'fields': new_rate.fields
            },
            on_change=add_view.add_button,
            no_change=add_view.cancel_button
        )
        return new_rate

    def update(self, updates):
        # Update a rate in UI
        view = navigate_to(self, 'Edit')
        view.fill_with(updates,
                       on_change=view.save_button,
                       no_change=view.cancel_button)

        view = self.create_view(navigator.get_class(self, 'Details').VIEW)
        view.flash.assert_no_error()

    def delete(self, cancel=False):
        """Delete a CB rate in the UI
        Args:
            cancel: boolean, whether to cancel the action on alert
        """
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove from the VMDB', handle_alert=(not cancel))
        view = self.create_view(navigator.get_class(self.parent, 'All').VIEW, wait=10)
        view.flash.assert_no_error()


@attr.s
class ComputeRateCollection(BaseCollection):
    ENTITY = ComputeRate
    RATE_TYPE = ENTITY.RATE_TYPE

    def create(self, description, currency=None, fields=None):
        """ Create a rate in the UI

        Args:
            description (str): name of the compute rate to create
            currency (str): - type of currency for the rate
            fields (dict): -  nested dictionary listing the Rate Details
                Key => Rate Details Description
                Value => dict
                    Key => Rate Details table column names
                    Value => Value to input in the table
        """
        rate = self.instantiate(description, currency, fields)

        view = navigate_to(self, 'Add')
        view.fill_with({'description': rate.description,
                        'currency': rate.currency,
                        'fields': rate.fields},
                       on_change=view.add_button,
                       no_change=view.cancel_button)

        view = self.create_view(navigator.get_class(self, 'All').VIEW, wait=10)
        view.flash.assert_no_error()

        return rate


@attr.s
class StorageRate(ComputeRate):
    # Methods and form for this are similar to that of ComputeRate, but navigation is different
    # from that of ComputeRate.
    pretty_attrs = ['description']
    RATE_TYPE = 'Storage'


class StorageRateCollection(BaseCollection):
    ENTITY = StorageRate
    RATE_TYPE = ENTITY.RATE_TYPE

    def create(self, description, currency=None, fields=None):
        """ Create a rate in the UI

        Args:
            description (str): name of the compute rate to create
            currency (str): - type of currency for the rate
            fields (dict): -  nested dictionary listing the Rate Details
                Key => Rate Details Description
                Value => dict
                    Key => Rate Details table column names
                    Value => Value to input in the table
        """
        storage_rate = self.instantiate(description, currency, fields)

        view = navigate_to(self, 'Add')
        view.fill_with({'description': storage_rate.description,
                        'currency': storage_rate.currency,
                        'fields': storage_rate.fields},
                       on_change=view.add_button,
                       no_change=view.cancel_button)

        view = self.create_view(navigator.get_class(self, 'All').VIEW, wait=10)
        view.flash.assert_no_error()

        return storage_rate


@navigator.register(ComputeRateCollection, 'All')
class ComputeRateAll(CFMENavigateStep):
    VIEW = RatesView
    prerequisite = NavigateToAttribute('appliance.server', 'IntelChargeback')

    def step(self, *args, **kwargs):
        self.view.rates.tree.click_path(
            "Rates",
            "Compute"
        )


@navigator.register(ComputeRateCollection, 'Add')
class ComputeRateNew(CFMENavigateStep):
    VIEW = AddComputeChargebackView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.view.toolbar.configuration.item_select("Add a new Chargeback Rate")


@navigator.register(ComputeRate, 'Details')
class ComputeRateDetails(CFMENavigateStep):
    VIEW = RatesDetailView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            self.view.rates.tree.click_path(
                "Rates",
                "Compute", self.obj.description
            )
        except CandidateNotFound as ex:
            raise ChargebackRateNotFound('Exception navigating to ComputeRate {} "Details": {}'
                                         .format(self.obj.description, ex))


@navigator.register(ComputeRate, 'Copy')
class ComputeRateCopy(CFMENavigateStep):
    VIEW = AddComputeChargebackView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.view.toolbar.configuration.item_select('Copy this Chargeback Rate')


@navigator.register(ComputeRate, 'Edit')
class ComputeRateEdit(CFMENavigateStep):
    VIEW = EditComputeChargebackView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.view.toolbar.configuration.item_select("Edit this Chargeback Rate")


@navigator.register(StorageRateCollection, 'All')
class StorageRateAll(CFMENavigateStep):
    VIEW = RatesView
    prerequisite = NavigateToAttribute('appliance.server', 'IntelChargeback')

    def step(self, *args, **kwargs):
        self.view.rates.tree.click_path(
            "Rates",
            "Storage"
        )


@navigator.register(StorageRateCollection, 'Add')
class StorageRateNew(CFMENavigateStep):
    VIEW = AddStorageChargebackView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.view.toolbar.configuration.item_select("Add a new Chargeback Rate")


@navigator.register(StorageRate, 'Details')
class StorageRateDetails(CFMENavigateStep):
    VIEW = RatesDetailView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            self.view.rates.tree.click_path(
                "Rates",
                "Storage", self.obj.description
            )
        except CandidateNotFound as ex:
            raise ChargebackRateNotFound('Exception navigating to StorageRate {} "Details": {}'
                                         .format(self.obj.description, ex))


@navigator.register(StorageRate, 'Edit')
class StorageRateEdit(CFMENavigateStep):
    VIEW = EditStorageChargebackView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.view.toolbar.configuration.item_select("Edit this Chargeback Rate")
