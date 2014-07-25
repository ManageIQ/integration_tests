# -*- coding: utf-8 -*-
import pytest

from cfme.storage import file_shares, filers, luns, volumes
from utils.conf import cfme_data
from utils.storage_managers import setup_storage_managers


@pytest.fixture(scope="module")
def storage_managers(request, use_storage):
    for sm in setup_storage_managers():
        sm.refresh_inventory()
        sm.refresh_status()
        sm.wait_until_updated()


def get_testing_data(obj):
    return cfme_data.get("storage", {}).get("testing", {}).get(obj, [])

pytestmark = [
    pytest.mark.usefixtures("storage_managers")
]


def test_file_shares_exist(soft_assert):
    shares_on_appliance = list(file_shares.all())
    for test_share in get_testing_data("file_shares"):
        for share in shares_on_appliance:
            matches = True
            for column, expected_value in test_share.iteritems():
                if getattr(share, column) != test_share[column]:
                    matches = False
            if matches:
                break
        else:
            soft_assert(False, "Share {} not found on appliance".format(str(test_share)))


def test_LUNs_exist(soft_assert):
    luns_on_appliance = list(luns.all())
    for test_lun in get_testing_data("luns"):
        for lun in luns_on_appliance:
            matches = True
            for column, expected_value in test_lun.iteritems():
                if getattr(lun, column) != test_lun[column]:
                    matches = False
            if matches:
                break
        else:
            soft_assert(False, "LUN {} not found on appliance".format(str(test_lun)))


def test_volumes_exist(soft_assert):
    volumes_on_appliance = list(volumes.all())
    for test_volume in get_testing_data("volumes"):
        for volume in volumes_on_appliance:
            matches = True
            for column, expected_value in test_volume.iteritems():
                if getattr(volume, column) != test_volume[column]:
                    matches = False
            if matches:
                break
        else:
            soft_assert(False, "Volume {} not found on appliance".format(str(test_volume)))


def test_filers_exist(soft_assert):
    filers_on_appliance = list(filers.all())
    for test_filer in get_testing_data("filers"):
        for filer in filers_on_appliance:
            matches = True
            for column, expected_value in test_filer.iteritems():
                if getattr(filer, column) != test_filer[column]:
                    matches = False
            if matches:
                break
        else:
            soft_assert(False, "Filer {} not found on appliance".format(str(test_filer)))
