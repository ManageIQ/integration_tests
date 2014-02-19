import pytest
import cfme.intelligence.chargeback as cb
import utils.randomness as random
import cfme.web_ui.flash as flash
from utils.update import update
import utils.error as error

pytestmark = [pytest.mark.usefixtures("logged_in")]


def new_compute_rate():
    return cb.ComputeRate(description='cb' + random.generate_random_string(),
                          cpu_alloc=(1000, cb.DAILY),
                          disk_io=(10, cb.DAILY),
                          fixed_cost_1=(100, cb.MONTHLY),
                          fixed_cost_2=(200, cb.DAILY),
                          memory_allocated=(10000, cb.MONTHLY),
                          memory_used=(4000, cb.WEEKLY),
                          network_io=(6000, cb.WEEKLY))


def new_storage_rate():
    return cb.StorageRate(description='cb' + random.generate_random_string(),
                          fixed_cost_2=(4000, cb.MONTHLY),
                          allocated_storage=(2000, cb.DAILY),
                          used_storage=(6000, cb.DAILY))


def test_add_new_compute_chargeback():
    ccb = new_compute_rate()
    ccb.create()
    flash.assert_message_match('Chargeback Rate "%s" was added' % ccb.description)


def test_compute_chargeback_duplicate_disallowed():
    ccb = new_compute_rate()
    ccb.create()
    with error.expected('Name already exists'):  # currently cfme just blows up
        ccb.create()


def test_add_new_storage_chargeback():
    scb = new_storage_rate()
    scb.create()
    flash.assert_message_match('Chargeback Rate "%s" was added' % scb.description)


def test_edit_compute_chargeback():
    ccb = new_compute_rate()
    ccb.create()
    with update(ccb) as ccb:
        ccb.description = ccb.description + "-edited"
        ccb.cpu_alloc = (5000, cb.DAILY)
        ccb.disk_io = (10, cb.WEEKLY)
        ccb.fixed_cost_1 = (200, cb.WEEKLY)
        ccb.fixed_cost_2 = (100, cb.DAILY)
        ccb.memory_allocated = (1, cb.HOURLY)
        ccb.memory_used = (2000, cb.WEEKLY)
        ccb.network_io = (4000, cb.DAILY)
    flash.assert_message_match('Chargeback Rate "%s" was saved' % ccb.description)


def test_edit_storage_chargeback():
    scb = new_storage_rate()
    scb.create()
    with update(scb) as scb:
        scb.description = scb.description + "-edited"
        scb.fixed_cost_2 = (2000, cb.MONTHLY)
        scb.allocated_storage = (3000, cb.WEEKLY)
        scb.used_storage = (6000, cb.MONTHLY)
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
