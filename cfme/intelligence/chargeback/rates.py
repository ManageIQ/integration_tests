# -*- coding: utf-8 -*-
# Page model for Intel->Chargeback->Rates.

from . import ChargebackView
from cached_property import cached_property
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from utils.pretty import Pretty
from utils.update import Updateable
from widgetastic.utils import ParametrizedLocator, ParametrizedString
from widgetastic.widget import Text, ParametrizedView
from widgetastic_manageiq import Select
from widgetastic_patternfly import Button, Input, Dropdown


class RatesView(ChargebackView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_chargeback and self.configuration.is_displayed and
            self.title.text == "Compute Chargeback Rates"
        )

    configuration = Dropdown('Configuration')


class RatesDetailView(ChargebackView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_chargeback and self.configuration.is_displayed and
            self.title.text == 'Compute Chargeback Rate "{}"'.format(
                self.context["object"].description) and
            self.rates.is_opened and
            self.rates.tree.currently_selected == [
                "Compute Chargeback Rates",
                self.context["object"].description
            ]
        )

    configuration = Dropdown('Configuration')


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

    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == 'Compute Chargeback Rates' and
            self.description.is_displayed)


class EditComputeChargebackView(AddComputeChargebackView):

    save_button = Button(title='Save Changes')
    reset_button = Button(title='Reset Changes')

    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == 'Compute Chargeback Rate "{}"'.format(self.obj.description))


class StorageChargebackView(RatesView):
    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == 'Storage Chargeback Rates')


class AddStorageChargebackView(AddComputeChargebackView):
    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == 'Storage Chargeback Rates' and
            self.description.is_displayed)


class EditStorageChargebackView(EditComputeChargebackView):
    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == 'Storage Chargeback Rate "{}"'.format(self.obj.description))


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

    def create(self):
        # Create a rate in UI
        view = navigate_to(self, 'New')
        view.fill_with({'description': self.description,
                        'currency': self.currency,
                        'fields': self.fields},
                       on_change=view.add_button,
                       no_change=view.cancel_button)

        view.flash.assert_success_message('Chargeback Rate "{}" was added'.format(
            self.description))

    def copy(self, *args, **kwargs):
        new_rate = ComputeRate(*args, **kwargs)
        add_view = navigate_to(self, 'Copy')
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

        view.flash.assert_success_message('Chargeback Rate "{}" was saved'.format(
            updates.get('description')))

    def delete(self):
        # Delete a rate in UI
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Remove from the VMDB', handle_alert=True)
        view.flash.assert_success_message('Chargeback Rate "{}": Delete successful'.format(
            self.description))


class StorageRate(ComputeRate):
    # Methods and form for this are similar to that of ComputeRate, but navigation is different
    # from that of ComputeRate.
    pretty_attrs = ['description']


@navigator.register(ComputeRate, 'All')
class ComputeRateAll(CFMENavigateStep):
    VIEW = RatesView
    prerequisite = NavigateToAttribute('appliance.server', 'IntelChargeback')

    def step(self):
        self.view.rates.tree.click_path(
            "Rates",
            "Compute"
        )


@navigator.register(ComputeRate, 'New')
class ComputeRateNew(CFMENavigateStep):
    VIEW = AddComputeChargebackView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.view.configuration.item_select("Add a new Chargeback Rate")


@navigator.register(ComputeRate, 'Details')
class ComputeRateDetails(CFMENavigateStep):
    VIEW = RatesDetailView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.view.rates.tree.click_path(
            "Rates",
            "Compute", self.obj.description
        )


@navigator.register(ComputeRate, 'Copy')
class ComputeRateCopy(CFMENavigateStep):
    VIEW = AddComputeChargebackView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.configuration.item_select('Copy this Chargeback Rate')


@navigator.register(ComputeRate, 'Edit')
class ComputeRateEdit(CFMENavigateStep):
    VIEW = EditComputeChargebackView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.configuration.item_select("Edit this Chargeback Rate")


@navigator.register(StorageRate, 'All')
class StorageRateAll(CFMENavigateStep):
    VIEW = StorageChargebackView
    prerequisite = NavigateToAttribute('appliance.server', 'IntelChargeback')

    def step(self):
        self.view.rates.tree.click_path(
            "Rates",
            "Storage"
        )


@navigator.register(StorageRate, 'New')
class StorageRateNew(CFMENavigateStep):
    VIEW = AddStorageChargebackView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.view.configuration.item_select("Add a new Chargeback Rate")


@navigator.register(StorageRate, 'Details')
class StorageRateDetails(CFMENavigateStep):
    VIEW = RatesDetailView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.view.rates.tree.click_path(
            "Rates",
            "Storage", self.obj.description
        )


@navigator.register(StorageRate, 'Edit')
class StorageRateEdit(CFMENavigateStep):
    VIEW = EditStorageChargebackView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.configuration.item_select("Edit this Chargeback Rate")
