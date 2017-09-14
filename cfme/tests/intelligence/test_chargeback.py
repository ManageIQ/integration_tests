# -*- coding: utf-8 -*-
import random
import fauxfactory
import pytest


import cfme.intelligence.chargeback.rates as cb
from cfme import test_requirements
from cfme.rest.gen_data import rates as _rates
from cfme.utils import error
from cfme.utils.blockers import BZ
from cfme.utils.update import update
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.chargeback
]


def with_random_per_time(**kw):
    kw['per_time'] = random.choice(['Hourly', 'Daily', 'Monthly', 'Weekly', 'Yearly'])
    return kw


@pytest.fixture
def chargeback_compute_rate():
    return cb.ComputeRate(
        description='cb' + fauxfactory.gen_alphanumeric(),
        fields={
            'Allocated CPU Count': with_random_per_time(fixed_rate='1000'),
            'Used Disk I/O': with_random_per_time(fixed_rate='10'),
            'Fixed Compute Cost 1': with_random_per_time(fixed_rate='100'),
            'Used Memory': with_random_per_time(fixed_rate='6000'),
            'Used CPU Cores': {'variable_rate': '0.05'}
        })


@pytest.fixture
def chargeback_storage_rate():
    return cb.StorageRate(
        description='cb' + fauxfactory.gen_alphanumeric(),
        fields={
            'Fixed Storage Cost 1': with_random_per_time(fixed_rate='100'),
            'Fixed Storage Cost 2': with_random_per_time(fixed_rate='300'),
            'Allocated Disk Storage': with_random_per_time(fixed_rate='6000'),
            'Used Disk Storage': with_random_per_time(variable_rate='0.1'),
        })


def test_add_new_compute_chargeback(chargeback_compute_rate):
    chargeback_compute_rate.create()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1441152, forced_streams=["5.8"])])
def test_compute_chargeback_duplicate_disallowed(chargeback_compute_rate):
    chargeback_compute_rate.create()
    with error.expected('Description has already been taken'):
        chargeback_compute_rate.create()


@pytest.mark.tier(3)
def test_add_new_storage_chargeback(chargeback_storage_rate):
    chargeback_storage_rate.create()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1468561, forced_streams=["5.8"])])
def test_edit_compute_chargeback(chargeback_compute_rate):
    chargeback_compute_rate.create()
    with update(chargeback_compute_rate):
        chargeback_compute_rate.description = chargeback_compute_rate.description + "-edited"
        chargeback_compute_rate.fields = {
            'Fixed Compute Cost 1': with_random_per_time(fixed_rate='500'),
            'Allocated CPU Count': with_random_per_time(fixed_rate='100'),
        }


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1468561, forced_streams=["5.8"])])
def test_edit_storage_chargeback(chargeback_storage_rate):
    chargeback_storage_rate.create()
    with update(chargeback_storage_rate):
        chargeback_storage_rate.description = chargeback_storage_rate.description + "-edited"
        chargeback_storage_rate.fields = {
            'Fixed Storage Cost 1': with_random_per_time(fixed_rate='500'),
            'Allocated Disk Storage': with_random_per_time(fixed_rate='100'),
        }


@pytest.mark.tier(3)
def test_delete_compute_chargeback(chargeback_compute_rate):
    chargeback_compute_rate.create()
    chargeback_compute_rate.delete()


@pytest.mark.tier(3)
def test_delete_storage_chargeback(chargeback_storage_rate):
    chargeback_storage_rate.create()
    chargeback_storage_rate.delete()


class TestRatesViaREST(object):
    @pytest.fixture(scope="function")
    def rates(self, request, appliance):
        response = _rates(request, appliance.rest_api)
        assert appliance.rest_api.response.status_code == 200
        return response

    @pytest.mark.tier(3)
    def test_create_rates(self, appliance, rates):
        """Tests creating rates.

        Metadata:
            test_flag: rest
        """
        for rate in rates:
            record = appliance.rest_api.collections.rates.get(id=rate.id)
            assert appliance.rest_api.response.status_code == 200
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
            assert appliance.rest_api.response.status_code == 200
        else:
            edited = []
            for rate in rates:
                new_description = "test_rate_{}".format(fauxfactory.gen_alphanumeric().lower())
                new_descriptions.append(new_description)
                edited.append(rate.action.edit(description=new_description))
                assert appliance.rest_api.response.status_code == 200
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
    def test_delete_rates_from_detil(self, appliance, rates, method):
        """Tests deleting rates from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == "delete" else 200
        for rate in rates:
            rate.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                rate.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_rates_from_collection(self, appliance, rates):
        """Tests deleting rates from collection.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.rates.action.delete(*rates)
        assert appliance.rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            appliance.rest_api.collections.rates.action.delete(*rates)
        assert appliance.rest_api.response.status_code == 404
