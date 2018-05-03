# -*- coding: utf-8 -*-
import random
import fauxfactory
import pytest


import cfme.intelligence.chargeback.rates as cb
from cfme import test_requirements
from cfme.rest.gen_data import rates as _rates
from cfme.utils.blockers import BZ
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


# TODO refactor to parametrize and collapse into CRUD tests
# single CRUD test function, parametrized on compute/storage + fixed/variable, will give us the
# same coverage with much less overlap and code duplication

def with_random_per_time(**kw):
    kw['per_time'] = random.choice(['Hourly', 'Daily', 'Monthly', 'Weekly', 'Yearly'])
    return kw


@pytest.fixture
def chargeback_compute_rate():
    # TODO add variable rate parametrization
    compute_rate = cb.ComputeRate(
        description='cb' + fauxfactory.gen_alphanumeric(),
        fields={
            'Allocated CPU Count': with_random_per_time(fixed_rate='1000'),
            'Used Disk I/O': with_random_per_time(fixed_rate='10'),
            'Fixed Compute Cost 1': with_random_per_time(fixed_rate='100'),
            'Used Memory': with_random_per_time(fixed_rate='6000'),
            'Used CPU Cores': {'variable_rate': '0.05'}
        })
    yield compute_rate
    if compute_rate.exists:
        compute_rate.delete()


def chargeback_storage_rate(rate_type='fixed'):
    if rate_type == 'fixed':
        rate = [{'fixed_rate': '6000'}, {'fixed_rate': '.1'}]
    elif rate_type == 'variable':
        rate = [{'variable_rate': '2000'}, {'variable_rate': '.6'}]
    else:
        raise ValueError('Storage rate type argument must be "fixed" or "variable"')

    return cb.StorageRate(
        description='cb' + fauxfactory.gen_alphanumeric(),
        fields={
            'Fixed Storage Cost 1': with_random_per_time(fixed_rate='100'),
            'Fixed Storage Cost 2': with_random_per_time(fixed_rate='300'),
            'Allocated Disk Storage': with_random_per_time(**rate[0]),
            'Used Disk Storage': with_random_per_time(**rate[1]),
        })


def test_add_new_compute_chargeback(chargeback_compute_rate):
    chargeback_compute_rate.create()
    view = chargeback_compute_rate.create_view(
        navigator.get_class(chargeback_compute_rate, 'All').VIEW)
    view.flash.assert_success_message('Chargeback Rate "{}" was added'
                                      .format(chargeback_compute_rate.description))
    assert chargeback_compute_rate.exists


@pytest.mark.tier(3)
def test_compute_chargeback_duplicate_disallowed(chargeback_compute_rate):
    chargeback_compute_rate.create()
    assert chargeback_compute_rate.exists
    with pytest.raises(AssertionError):
        chargeback_compute_rate.create()
    # view should still be on the add form
    view = chargeback_compute_rate.create_view(
        navigator.get_class(chargeback_compute_rate, 'Add').VIEW)
    view.flash.assert_message('Description has already been taken', t='error')
    # cancel form, check all redirect
    view.cancel_button.click()
    view = chargeback_compute_rate.create_view(
        navigator.get_class(chargeback_compute_rate, 'All').VIEW)
    assert view.is_displayed
    view.flash.assert_success_message('Add of new Chargeback Rate was cancelled by the user')


@pytest.mark.tier(3)
@pytest.mark.parametrize('storage_chargeback',
                         ['fixed', 'variable'],
                         ids=['fixed_storage_rate', 'variable_storage_rate'])
@pytest.mark.meta(blockers=[
    BZ(1532368, forced_streams='5.9',
       unblock=lambda storage_chargeback: 'variable' not in storage_chargeback)])
def test_add_new_storage_chargeback(storage_chargeback, request):
    cb_rate = chargeback_storage_rate(storage_chargeback)

    @request.addfinalizer
    def _cleanup():
        if cb_rate.exists:
            cb_rate.delete()

    cb_rate.create()
    view = cb_rate.create_view(
        navigator.get_class(cb_rate, 'All').VIEW)
    view.flash.assert_success_message(
        'Chargeback Rate "{}" was added'.format(cb_rate.description))
    assert cb_rate.exists


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1468561, forced_streams=["5.8"])])
def test_edit_compute_chargeback(chargeback_compute_rate):
    chargeback_compute_rate.create()
    assert chargeback_compute_rate.exists
    with update(chargeback_compute_rate):
        chargeback_compute_rate.description = chargeback_compute_rate.description + "-edited"
        chargeback_compute_rate.fields = {
            'Fixed Compute Cost 1': with_random_per_time(fixed_rate='500'),
            'Allocated CPU Count': with_random_per_time(fixed_rate='100'),
        }
    view = chargeback_compute_rate.create_view(
        navigator.get_class(chargeback_compute_rate, 'Details').VIEW)
    view.flash.assert_success_message(
        'Chargeback Rate "{}" was saved'.format(chargeback_compute_rate.description))
    assert chargeback_compute_rate.exists


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1468561, forced_streams=["5.8"])])
def test_edit_storage_chargeback():
    storage_rate = chargeback_storage_rate()  # TODO parametrize on variable
    storage_rate.create()
    assert storage_rate.exists
    with update(storage_rate):
        storage_rate.description = storage_rate.description + "-edited"
        storage_rate.fields = {
            'Fixed Storage Cost 1': with_random_per_time(fixed_rate='500'),
            'Allocated Disk Storage': with_random_per_time(fixed_rate='100'),
        }
    view = storage_rate.create_view(
        navigator.get_class(storage_rate, 'Details').VIEW)
    view.flash.assert_success_message(
        'Chargeback Rate "{}" was saved'.format(storage_rate.description))
    assert storage_rate.exists


@pytest.mark.tier(3)
def test_delete_compute_chargeback(chargeback_compute_rate):
    chargeback_compute_rate.create()
    assert chargeback_compute_rate.exists

    chargeback_compute_rate.delete()
    view = chargeback_compute_rate.create_view(
        navigator.get_class(chargeback_compute_rate, 'Details').VIEW)
    view.flash.assert_success_message(
        'Chargeback Rate "{}": Delete successful'.format(chargeback_compute_rate.description))
    assert not chargeback_compute_rate.exists


@pytest.mark.tier(3)
def test_delete_storage_chargeback():
    storage_rate = chargeback_storage_rate()  # TODO parametrize on variable
    storage_rate.create()
    assert storage_rate.exists

    storage_rate.delete()
    view = storage_rate.create_view(
        navigator.get_class(storage_rate, 'Details').VIEW)
    view.flash.assert_success_message(
        'Chargeback Rate "{}": Delete successful'.format(storage_rate.description))
    assert not storage_rate.exists


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
        """
        delete_resources_from_detail(rates, method=method)

    @pytest.mark.tier(3)
    def test_delete_rates_from_collection(self, rates):
        """Tests deleting rates from collection.

        Metadata:
            test_flag: rest
        """
        delete_resources_from_collection(rates)
