# -*- coding: utf-8 -*-
import random
import fauxfactory
import pytest


import cfme.intelligence.chargeback.rates as cb
from cfme import test_requirements
from cfme.rest.gen_data import rates as _rates
from cfme.utils.rest import (
    assert_response,
    delete_resources_from_collection,
    delete_resources_from_detail,
)
from cfme.utils.update import update
from cfme.utils.wait import wait_for
from cfme.utils.appliance.implementations.ui import navigator


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.chargeback
]


def with_random_per_time(**kw):
    kw['per_time'] = random.choice(['Hourly', 'Daily', 'Monthly', 'Weekly', 'Yearly'])
    return kw


@pytest.fixture()
def chargeback_rate(rate_resource, rate_type, rate_action, request):
    if 'fixed' in rate_type:
        rate = [{'fixed_rate': '6000'}, {'fixed_rate': '.1'}]
    elif 'variable' in rate_type:
        rate = [{'variable_rate': '2000'}, {'variable_rate': '.6'}]
    else:
        raise ValueError('Compute rate type argument must be "fixed" or "variable"')

    if rate_resource == 'compute':
        rate = cb.ComputeRate(
            description='cb_{}_{}_{}_{}'.format(fauxfactory.gen_alphanumeric(), rate_type,
                rate_resource, rate_action),
            fields={
                'Allocated CPU Count': with_random_per_time(fixed_rate='1000'),
                'Used Disk I/O': with_random_per_time(fixed_rate='10'),
                'Fixed Compute Cost 1': with_random_per_time(fixed_rate='100'),
                'Used Memory': with_random_per_time(**rate[0]),
                'Used CPU Cores': with_random_per_time(**rate[1]),
            })

    elif rate_resource == 'storage':
        rate = cb.StorageRate(
            description='cb_{}_{}_{}_{}'.format(fauxfactory.gen_alphanumeric(), rate_type,
                rate_resource, rate_action),
            fields={
                'Fixed Storage Cost 1': with_random_per_time(fixed_rate='100'),
                'Fixed Storage Cost 2': with_random_per_time(fixed_rate='300'),
                'Allocated Disk Storage': with_random_per_time(**rate[0]),
                'Used Disk Storage': with_random_per_time(**rate[1]),
            })

    @request.addfinalizer
    def _cleanup():
        if rate.exists:
            rate.delete()
    return rate


def test_compute_chargeback_duplicate_disallowed(request):
    """
    Polarion:
        assignee: nachandr
        casecomponent: candu
        caseimportance: low
        initialEstimate: 1/12h
    """
    cb_rate = chargeback_rate('compute', 'fixed', 'add', request)

    cb_rate.create()
    assert cb_rate.exists
    with pytest.raises(AssertionError):
        cb_rate.create()
    # view should still be on the add form
    view = cb_rate.create_view(
        navigator.get_class(cb_rate, 'Add').VIEW)
    view.flash.assert_message('Description has already been taken', t='error')
    # cancel form, check all redirect
    view.cancel_button.click()
    view = cb_rate.create_view(
        navigator.get_class(cb_rate, 'All').VIEW)
    assert view.is_displayed
    view.flash.assert_success_message('Add of new Chargeback Rate was cancelled by the user')


@pytest.mark.parametrize('rate_resource', ['compute', 'storage'])
@pytest.mark.parametrize('rate_type', ['fixed', 'variable'])
@pytest.mark.parametrize('rate_action', ['add', 'delete', 'edit'])
def test_chargeback_rate(rate_resource, rate_type, rate_action, request):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    cb_rate = chargeback_rate(rate_resource, rate_type, rate_action, request)
    cb_rate.create()

    view = cb_rate.create_view(
        navigator.get_class(cb_rate, 'All').VIEW)
    view.flash.assert_success_message(
        'Chargeback Rate "{}" was added'.format(cb_rate.description))
    assert cb_rate.exists

    if 'delete' in rate_action:
        cb_rate.delete()
        view = cb_rate.create_view(
            navigator.get_class(cb_rate, 'Details').VIEW)
        view.flash.assert_success_message(
            'Chargeback Rate "{}": Delete successful'.format(cb_rate.description))
        assert not cb_rate.exists

    if 'update' in rate_action:
        with update(cb_rate):
            cb_rate.description = '{}_edited'.format(cb_rate.description)
            if 'compute' in rate_action:
                cb_rate.fields = {
                    'Fixed Compute Cost 1': with_random_per_time(fixed_rate='500'),
                    'Allocated CPU Count': with_random_per_time(fixed_rate='100'),
                }
            elif 'storage' in rate_action:
                cb_rate.fields = {
                    'Fixed Storage Cost 1': with_random_per_time(fixed_rate='100'),
                    'Fixed Storage Cost 2': with_random_per_time(fixed_rate='200'),
                }
        view = cb_rate.create_view(
            navigator.get_class(cb_rate, 'Details').VIEW)
        view.flash.assert_success_message(
            'Chargeback Rate "{}" was saved'.format(cb_rate.description))
        assert cb_rate.exists


class TestRatesViaREST(object):
    @pytest.fixture(scope="function")
    def rates(self, request, appliance):
        response = _rates(request, appliance.rest_api)
        assert_response(appliance)
        return response

    @pytest.mark.tier(3)
    def test_create_rates(self, appliance, rates):
        """Tests creating rates.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nachandr
            casecomponent: candu
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
            assignee: nachandr
            casecomponent: candu
            caseimportance: low
            initialEstimate: 1/3h
        """
        new_descriptions = []
        if multiple:
            rates_data_edited = []
            for rate in rates:
                new_description = "test_rate_{}".format(fauxfactory.gen_alphanumeric().lower())
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
                new_description = "test_rate_{}".format(fauxfactory.gen_alphanumeric().lower())
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
            assignee: nachandr
            casecomponent: candu
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
            assignee: nachandr
            casecomponent: candu
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_collection(rates)
