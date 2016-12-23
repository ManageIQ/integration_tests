# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import cfme.intelligence.chargeback as cb
import cfme.web_ui.flash as flash
import utils.error as error

from cfme import test_requirements
from cfme.rest.gen_data import rates as _rates
from utils.update import update
from utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.chargeback
]


def new_compute_rate():
    return cb.ComputeRate(description='cb' + fauxfactory.gen_alphanumeric(),
                          cpu_alloc=(1000, cb.HOURLY),
                          disk_io=(10, cb.HOURLY),
                          compute_fixed_1=(100, cb.HOURLY),
                          compute_fixed_2=(200, cb.HOURLY),
                          mem_alloc=(10000, cb.HOURLY),
                          mem_used=(4000, cb.HOURLY),
                          net_io=(6000, cb.HOURLY))


def new_storage_rate():
    return cb.StorageRate(description='cb' + fauxfactory.gen_alphanumeric(),
                          storage_fixed_2=(4000, cb.HOURLY),
                          storage_alloc=(2000, cb.HOURLY),
                          storage_used=(6000, cb.HOURLY))


def test_add_new_compute_chargeback():
    ccb = new_compute_rate()
    ccb.create()
    flash.assert_message_match('Chargeback Rate "{}" was added'.format(ccb.description))


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1073366])
def test_compute_chargeback_duplicate_disallowed():
    ccb = new_compute_rate()
    ccb.create()
    with error.expected('Description has already been taken'):
        ccb.create()


@pytest.mark.tier(3)
def test_add_new_storage_chargeback():
    scb = new_storage_rate()
    scb.create()
    flash.assert_message_match('Chargeback Rate "{}" was added'.format(scb.description))


@pytest.mark.tier(3)
def test_edit_compute_chargeback():
    ccb = new_compute_rate()
    ccb.create()
    with update(ccb):
        ccb.description = ccb.description + "-edited"
        ccb.cpu_alloc = (5000, cb.HOURLY)
        ccb.disk_io = (10, cb.HOURLY)
        ccb.compute_fixed_1 = (200, cb.HOURLY)
        ccb.compute_fixed_2 = (100, cb.HOURLY)
        ccb.mem_alloc = (1, cb.HOURLY)
        ccb.mem_used = (2000, cb.HOURLY)
        ccb.net_io = (4000, cb.HOURLY)
    flash.assert_message_match('Chargeback Rate "{}" was saved'.format(ccb.description))


@pytest.mark.tier(3)
def test_edit_storage_chargeback():
    scb = new_storage_rate()
    scb.create()
    with update(scb):
        scb.description = scb.description + "-edited"
        scb.storage_fixed_2 = (2000, cb.HOURLY)
        scb.storage_alloc = (3000, cb.HOURLY)
        scb.storage_used = (6000, cb.HOURLY)
    flash.assert_message_match('Chargeback Rate "{}" was saved'.format(scb.description))


@pytest.mark.tier(3)
def test_delete_compute_chargeback():
    ccb = new_compute_rate()
    ccb.create()
    ccb.delete()
    flash.assert_message_match('Chargeback Rate "{}": Delete successful'.format(ccb.description))


@pytest.mark.tier(3)
def test_delete_storage_chargeback():
    scb = new_storage_rate()
    scb.create()
    scb.delete()
    flash.assert_message_match('Chargeback Rate "{}": Delete successful'.format(scb.description))


class TestRatesViaREST(object):
    @pytest.fixture(scope="function")
    def rates(self, request, rest_api):
        return _rates(request, rest_api)

    @pytest.mark.parametrize(
        "multiple", [False, True],
        ids=["one_request", "multiple_requests"])
    @pytest.mark.tier(3)
    def test_edit_rates(self, rest_api, rates, multiple):
        if multiple:
            new_descriptions = []
            rates_data_edited = []
            for rate in rates:
                new_description = fauxfactory.gen_alphanumeric().lower()
                new_descriptions.append(new_description)
                rate.reload()
                rates_data_edited.append({
                    "href": rate.href,
                    "description": "test_category_{}".format(new_description),
                })
            rest_api.collections.rates.action.edit(*rates_data_edited)
            for new_description in new_descriptions:
                wait_for(
                    lambda: rest_api.collections.rates.find_by(description=new_description),
                    num_sec=180,
                    delay=10,
                )
        else:
            rate = rest_api.collections.rates.get(description=rates[0].description)
            new_description = 'test_rate_{}'.format(fauxfactory.gen_alphanumeric().lower())
            rate.action.edit(description=new_description)
            wait_for(
                lambda: rest_api.collections.rates.find_by(description=new_description),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "multiple", [False, True],
        ids=["one_request", "multiple_requests"])
    def test_delete_rates(self, rest_api, rates, multiple):
        if multiple:
            rest_api.collections.rates.action.delete(*rates)
            with error.expected("ActiveRecord::RecordNotFound"):
                rest_api.collections.rates.action.delete(*rates)
        else:
            rate = rates[0]
            rate.action.delete()
            with error.expected("ActiveRecord::RecordNotFound"):
                rate.action.delete()
