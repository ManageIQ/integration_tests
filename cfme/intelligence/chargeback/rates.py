# -*- coding: utf-8 -*-
# Page model for Intel->Chargeback->Rates.
from wait_for import TimedOutError

from cached_property import cached_property
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.utils import ParametrizedLocator, ParametrizedString
from widgetastic.widget import Text, ParametrizedView, View
from widgetastic_patternfly import Button, Input, Dropdown

from cfme.exceptions import ChargebackRateNotFound, displayed_not_implemented
from cfme.utils import ParamClassName
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from cfme.utils.blockers import BZ
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from widgetastic_manageiq import Select, Table
from . import ChargebackView


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
        # BZ 1532701 for singular title on redirection to this page, but not direct navigation
        if BZ(1532701, forced_streams='5.9').blocks:
            title_test = ("{} Chargeback Rate".format(self.context['object'].RATE_TYPE)
                          in self.title.text)
        else:
            title_test = ("{} Chargeback Rates".format(self.context['object'].RATE_TYPE) ==
                          self.title.text)
        return (
            self.in_rates and
            self.rates.tree.currently_selected == ['Rates',
                                                   self.context['object'].RATE_TYPE] and
            title_test)

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

    is_displayed = displayed_not_implemented


class EditComputeChargebackView(AddComputeChargebackView):

    save_button = Button(title='Save Changes')
    reset_button = Button(title='Reset Changes')

    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == 'Compute Chargeback Rate "{}"'
                               .format(self.context['object'].description)
        )


class AddStorageChargebackView(AddComputeChargebackView):
    pass


class EditStorageChargebackView(EditComputeChargebackView):
    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == 'Storage Chargeback Rate "{}"'
                               .format(self.context['object'].description)
        )


# TODO Inherit BaseEntity and create a parent collection class
class ComputeRate(Updateable, Pretty, Navigatable):
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
        return self.fields.get(name)

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
        except (ChargebackRateNotFound, TimedOutError):
            return False
        else:
            return True

    def create(self):
        # Create a rate in UI
        view = navigate_to(self, 'Add', wait_for_view=0)
        view.fill_with({'description': self.description,
                        'currency': self.currency,
                        'fields': self.fields},
                       on_change=view.add_button,
                       no_change=view.cancel_button)

        view = self.create_view(navigator.get_class(self, 'All').VIEW)
        assert view.is_displayed
        view.flash.assert_no_error()

    def copy(self, *args, **kwargs):
        new_rate = ComputeRate(*args, **kwargs)
        add_view = navigate_to(self, 'Copy', wait_for_view=0)
        add_view.fill_with({'description': new_rate.description,
                            'currency': new_rate.currency,
                            'fields': new_rate.fields},
                           on_change=add_view.add_button,
                           no_change=add_view.cancel_button)

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
        view = self.create_view(navigator.get_class(self, 'All').VIEW)
        assert view.is_displayed
        view.flash.assert_no_error()


class StorageRate(ComputeRate):
    # Methods and form for this are similar to that of ComputeRate, but navigation is different
    # from that of ComputeRate.
    pretty_attrs = ['description']
    RATE_TYPE = 'Storage'


@navigator.register(ComputeRate, 'All')
class ComputeRateAll(CFMENavigateStep):
    VIEW = RatesView
    prerequisite = NavigateToAttribute('appliance.server', 'IntelChargeback')

    def step(self):
        self.view.rates.tree.click_path(
            "Rates",
            "Compute"
        )


@navigator.register(ComputeRate, 'Add')
class ComputeRateNew(CFMENavigateStep):
    VIEW = AddComputeChargebackView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.view.toolbar.configuration.item_select("Add a new Chargeback Rate")


@navigator.register(ComputeRate, 'Details')
class ComputeRateDetails(CFMENavigateStep):
    VIEW = RatesDetailView
    prerequisite = NavigateToSibling('All')

    def step(self):
        try:
            self.view.rates.tree.click_path(
                "Rates",
                "Compute", self.obj.description
            )
        except Exception as ex:
            # TODO don't diaper here
            raise ChargebackRateNotFound('Exception navigating to ComputeRate {} "Details": {}'
                                         .format(self.obj.description, ex))


@navigator.register(ComputeRate, 'Copy')
class ComputeRateCopy(CFMENavigateStep):
    VIEW = AddComputeChargebackView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.toolbar.configuration.item_select('Copy this Chargeback Rate')


@navigator.register(ComputeRate, 'Edit')
class ComputeRateEdit(CFMENavigateStep):
    VIEW = EditComputeChargebackView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.toolbar.configuration.item_select("Edit this Chargeback Rate")


@navigator.register(StorageRate, 'All')
class StorageRateAll(CFMENavigateStep):
    VIEW = RatesView
    prerequisite = NavigateToAttribute('appliance.server', 'IntelChargeback')

    def step(self):
        self.view.rates.tree.click_path(
            "Rates",
            "Storage"
        )


@navigator.register(StorageRate, 'Add')
class StorageRateNew(CFMENavigateStep):
    VIEW = AddStorageChargebackView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.view.toolbar.configuration.item_select("Add a new Chargeback Rate")


@navigator.register(StorageRate, 'Details')
class StorageRateDetails(CFMENavigateStep):
    VIEW = RatesDetailView
    prerequisite = NavigateToSibling('All')

    def step(self):
        try:
            self.view.rates.tree.click_path(
                "Rates",
                "Storage", self.obj.description
            )
        except Exception as ex:
            # TODO don't diaper here
            raise ChargebackRateNotFound('Exception navigating to StorageRate {} "Details": {}'
                                         .format(self.obj.description, ex))


@navigator.register(StorageRate, 'Edit')
class StorageRateEdit(CFMENavigateStep):
    VIEW = EditStorageChargebackView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.toolbar.configuration.item_select("Edit this Chargeback Rate")
