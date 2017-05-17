# -*- coding: utf-8 -*-
import random
import fauxfactory
import pytest


import cfme.intelligence.chargeback as cb
from cfme import test_requirements
from cfme.rest.gen_data import rates as _rates
from utils import error
from utils.blockers import BZ
from utils.version import current_version
from utils.update import update
from utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.chargeback
]

per_time = ['Hourly', 'Daily', 'Monthly', 'Weekly', 'Yearly'] if current_version() >= '5.7' \
    else ['Hourly', 'Monthly']


def new_compute_rate():
    return cb.ComputeRate(description='cb' + fauxfactory.gen_alphanumeric(),
                    fields={'Allocated CPU Count':
                            {'per_time': random.choice(per_time), 'fixed_rate': '1000'},
                            'Used Disk I/O':
                            {'per_time': random.choice(per_time), 'fixed_rate': '10'},
                            'Fixed Compute Cost 1':
                            {'per_time': random.choice(per_time), 'fixed_rate': '100'},
                            'Used Memory':
                            {'per_time': random.choice(per_time), 'fixed_rate': '6000'},
                            'Used CPU Cores': {'variable_rate': '0.05'}})


def new_storage_rate():
    return cb.StorageRate(description='cb' + fauxfactory.gen_alphanumeric(),
                    fields={'Fixed Storage Cost 1':
                            {'per_time': random.choice(per_time), 'fixed_rate': '100'},
                            'Fixed Storage Cost 2':
                            {'per_time': random.choice(per_time), 'fixed_rate': '300'},
                            'Allocated Disk Storage':
                            {'per_time': random.choice(per_time), 'fixed_rate': '6000'},
                            'Used Disk Storage':
                            {'per_time': random.choice(per_time), 'variable_rate': '0.1'}})


def test_add_new_compute_chargeback():
    ccb = new_compute_rate()
    ccb.create()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1441152, forced_streams=["5.8"])])
def test_compute_chargeback_duplicate_disallowed():
    ccb = new_compute_rate()
    ccb.create()
    with error.expected('Description has already been taken'):
        ccb.create()


@pytest.mark.tier(3)
def test_add_new_storage_chargeback():
    scb = new_storage_rate()
    scb.create()


@pytest.mark.tier(3)
def test_edit_compute_chargeback():
    ccb = new_compute_rate()
    ccb.create()
    with update(ccb):
        ccb.description = ccb.description + "-edited"
        ccb.fields = {'Fixed Compute Cost 1':
                      {'per_time': random.choice(per_time), 'fixed_rate': '500'},
                      'Allocated CPU Count':
                      {'per_time': random.choice(per_time), 'fixed_rate': '100'}}


@pytest.mark.tier(3)
def test_edit_storage_chargeback():
    scb = new_storage_rate()
    scb.create()
    with update(scb):
        scb.description = scb.description + "-edited"
        scb.fields = {'Fixed Storage Cost 1':
                      {'per_time': random.choice(per_time), 'fixed_rate': '500'},
                      'Allocated Disk Storage':
                      {'per_time': random.choice(per_time), 'fixed_rate': '100'}}


@pytest.mark.tier(3)
def test_delete_compute_chargeback():
    ccb = new_compute_rate()
    ccb.create()
    ccb.delete()


@pytest.mark.tier(3)
def test_delete_storage_chargeback():
    scb = new_storage_rate()
    scb.create()
    scb.delete()


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
            rate.reload()
            record, _ = wait_for(
                lambda: appliance.rest_api.collections.rates.find_by(
                    description=new_descriptions[index]) or False,
                num_sec=180,
                delay=10,
            )
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
