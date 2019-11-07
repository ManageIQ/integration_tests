import random

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.rest.gen_data import rates as _rates
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.update import update
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.chargeback
]


def random_per_time(**kw):
    kw['per_time'] = random.choice(['Hourly', 'Daily', 'Monthly', 'Weekly', 'Yearly'])
    return kw


FIXED_RATE = [{'fixed_rate': '6000'}, {'fixed_rate': '.1'}]
VARIABLE_RATE = [{'variable_rate': '2000'}, {'variable_rate': '.6'}]


@pytest.fixture(scope='function')
def chargeback_rate(appliance, rate_resource, rate_type, rate_action):
    if rate_type not in ['fixed', 'variable']:
        pytest.fail('Chargeback "rate_type" argument must be "fixed" or "variable"')
    rate_values = FIXED_RATE if rate_type == 'fixed' else VARIABLE_RATE

    rate_description = ('cb_{rand}_{type}_{resource}_{action}'
                        .format(rand=fauxfactory.gen_alphanumeric(),
                                type=rate_type,
                                resource=rate_resource,
                                action=rate_action))

    if rate_resource == 'compute':
        rate = appliance.collections.compute_rates.create(
            description=rate_description,
            fields={
                'Allocated CPU Count': random_per_time(fixed_rate='1000'),
                'Used Disk I/O': random_per_time(fixed_rate='10'),
                'Fixed Compute Cost 1': random_per_time(fixed_rate='100'),
                'Used Memory': random_per_time(**rate_values[0]),
                'Used CPU Cores': random_per_time(**rate_values[1]),
            }
        )

    elif rate_resource == 'storage':
        rate = appliance.collections.storage_rates.create(
            description=rate_description,
            fields={
                'Fixed Storage Cost 1': random_per_time(fixed_rate='100'),
                'Fixed Storage Cost 2': random_per_time(fixed_rate='300'),
                'Allocated Disk Storage': random_per_time(**rate_values[0]),
                'Used Disk Storage': random_per_time(**rate_values[1]),
            }
        )

    yield rate

    rate.delete_if_exists()


@pytest.mark.parametrize('rate_resource', ['compute', 'storage'])
@pytest.mark.parametrize('rate_type', ['fixed', 'variable'])
@pytest.mark.parametrize('rate_action', ['add'])
def test_chargeback_duplicate_disallowed(
    chargeback_rate, rate_resource, rate_type, rate_action, appliance
):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """
    cb_rate = chargeback_rate  # for brevity
    assert cb_rate.exists
    with pytest.raises((AssertionError, TimedOutError)):  # create method might raise either
        if rate_resource == 'compute':
            appliance.collections.compute_rates.create(
                description=cb_rate.description,
                fields=cb_rate.fields
            )
        elif rate_resource == 'storage':
            appliance.collections.storage_rates.create(
                description=cb_rate.description,
                fields=cb_rate.fields
            )
    # view should still be on the add form
    view = cb_rate.create_view(navigator.get_class(cb_rate.parent, 'Add').VIEW, wait=10)
    view.flash.assert_message('Description has already been taken', t='error')
    # cancel form, check all redirect
    view.cancel_button.click()

    view = cb_rate.create_view(navigator.get_class(cb_rate.parent, 'All').VIEW, wait=10)
    view.flash.assert_success_message('Add of new Chargeback Rate was cancelled by the user')


@pytest.mark.parametrize('rate_resource', ['compute', 'storage'])
@pytest.mark.parametrize('rate_type', ['fixed', 'variable'])
@pytest.mark.parametrize('rate_action', ['add', 'delete', 'edit'])
def test_chargeback_rate(rate_resource, rate_type, rate_action, request, chargeback_rate):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    cb_rate = chargeback_rate  # for brevity

    view = cb_rate.create_view(navigator.get_class(cb_rate.parent, 'All').VIEW, wait=10)
    view.flash.assert_success_message(
        'Chargeback Rate "{}" was added'.format(cb_rate.description))
    assert cb_rate.exists

    if rate_action == 'delete':
        cb_rate.delete()
        view.flash.assert_success_message(
            'Chargeback Rate "{}": Delete successful'.format(cb_rate.description))
        assert not cb_rate.exists

    if rate_action == 'edit':
        with update(cb_rate):
            cb_rate.description = '{}_edited'.format(cb_rate.description)
            if rate_resource == 'compute':
                cb_rate.fields = {
                    'Fixed Compute Cost 1': random_per_time(fixed_rate='500'),
                    'Allocated CPU Count': random_per_time(fixed_rate='100'),
                }
            elif rate_resource == 'storage':
                cb_rate.fields = {
                    'Fixed Storage Cost 1': random_per_time(fixed_rate='100'),
                    'Fixed Storage Cost 2': random_per_time(fixed_rate='200'),
                }
        view = cb_rate.create_view(navigator.get_class(cb_rate, 'Details').VIEW, wait=10)
        view.flash.assert_success_message(
            'Chargeback Rate "{}" was saved'.format(cb_rate.description))
        assert cb_rate.exists


class TestRatesViaREST(object):
    @pytest.fixture(scope="function")
    def rates(self, request, appliance):
        response = _rates(request, appliance)
        assert_response(appliance)
        return response

    @pytest.mark.tier(3)
    def test_create_rates(self, appliance, rates):
        """Tests creating rates.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: tpapaioa
            casecomponent: CandU
            caseimportance: low
            initialEstimate: 1/4h
        """
        for rate in rates:
            record = appliance.rest_api.collections.rates.get(id=rate.id)
            assert_response(appliance)
            assert record.description == rate.description

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "multiple", [False, True],
        ids=["one_request", "multiple_requests"])
    def test_edit_rates(self, appliance, rates, multiple):
        """Tests editing rates.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: tpapaioa
            casecomponent: CandU
            caseimportance: low
            initialEstimate: 1/3h
        """
        new_descriptions = []
        if multiple:
            rates_data_edited = []
            for rate in rates:
                new_description = fauxfactory.gen_alphanumeric(15, start="test_rate_").lower()
                new_descriptions.append(new_description)
                rate.reload()
                rates_data_edited.append({
                    "href": rate.href,
                    "description": new_description,
                })
            edited = appliance.rest_api.collections.rates.action.edit(*rates_data_edited)
            assert_response(appliance)
        else:
            edited = []
            for rate in rates:
                new_description = fauxfactory.gen_alphanumeric(15, start="test_rate_").lower()
                new_descriptions.append(new_description)
                edited.append(rate.action.edit(description=new_description))
                assert_response(appliance)
        assert len(edited) == len(rates)
        for index, rate in enumerate(rates):
            record, _ = wait_for(
                lambda: appliance.rest_api.collections.rates.find_by(
                    description=new_descriptions[index]) or False,
                num_sec=180,
                delay=10,
            )
            rate.reload()
            assert rate.description == edited[index].description == record[0].description

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_rates_from_detail(self, rates, method):
        """Tests deleting rates from detail.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: tpapaioa
            casecomponent: CandU
            caseimportance: medium
            initialEstimate: 1/20h
        """
        delete_resources_from_detail(rates, method=method)

    @pytest.mark.tier(3)
    def test_delete_rates_from_collection(self, rates):
        """Tests deleting rates from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: tpapaioa
            casecomponent: CandU
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_collection(rates)
