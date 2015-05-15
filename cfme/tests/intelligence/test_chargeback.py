# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import cfme.intelligence.chargeback as cb
import cfme.web_ui.flash as flash
from utils.update import update
import utils.error as error

pytestmark = [pytest.mark.usefixtures("logged_in")]


def new_compute_rate():
    return cb.ComputeRate(description='cb' + fauxfactory.gen_alphanumeric(),
                          cpu_alloc=(1000, cb.DAILY),
                          disk_io=(10, cb.DAILY),
                          compute_fixed_1=(100, cb.MONTHLY),
                          compute_fixed_2=(200, cb.DAILY),
                          mem_alloc=(10000, cb.MONTHLY),
                          mem_used=(4000, cb.WEEKLY),
                          net_io=(6000, cb.WEEKLY))


def new_storage_rate():
    return cb.StorageRate(description='cb' + fauxfactory.gen_alphanumeric(),
                          storage_fixed_2=(4000, cb.MONTHLY),
                          storage_alloc=(2000, cb.DAILY),
                          storage_used=(6000, cb.DAILY))


def test_add_new_compute_chargeback():
    ccb = new_compute_rate()
    ccb.create()
    flash.assert_message_match('Chargeback Rate "%s" was added' % ccb.description)


@pytest.mark.meta(blockers=[1073366])
def test_compute_chargeback_duplicate_disallowed():
    ccb = new_compute_rate()
    ccb.create()
    with error.expected('Description has already been taken'):
        ccb.create()


def test_add_new_storage_chargeback():
    scb = new_storage_rate()
    scb.create()
    flash.assert_message_match('Chargeback Rate "%s" was added' % scb.description)


def test_edit_compute_chargeback():
    ccb = new_compute_rate()
    ccb.create()
    with update(ccb):
        ccb.description = ccb.description + "-edited"
        ccb.cpu_alloc = (5000, cb.DAILY)
        ccb.disk_io = (10, cb.WEEKLY)
        ccb.compute_fixed_1 = (200, cb.WEEKLY)
        ccb.compute_fixed_2 = (100, cb.DAILY)
        ccb.mem_alloc = (1, cb.HOURLY)
        ccb.mem_used = (2000, cb.WEEKLY)
        ccb.net_io = (4000, cb.DAILY)
    flash.assert_message_match('Chargeback Rate "%s" was saved' % ccb.description)


def test_edit_storage_chargeback():
    scb = new_storage_rate()
    scb.create()
    with update(scb):
        scb.description = scb.description + "-edited"
        scb.storage_fixed_2 = (2000, cb.MONTHLY)
        scb.storage_alloc = (3000, cb.WEEKLY)
        scb.storage_used = (6000, cb.MONTHLY)
    flash.assert_message_match('Chargeback Rate "%s" was saved' % scb.description)


def test_delete_compute_chargeback():
    ccb = new_compute_rate()
    ccb.create()
    ccb.delete()
    flash.assert_message_match('The selected Chargeback Rate was deleted')


def test_delete_storage_chargeback():
    scb = new_storage_rate()
    scb.create()
    scb.delete()
    flash.assert_message_match('The selected Chargeback Rate was deleted')
