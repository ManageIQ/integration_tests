# -*- coding: utf-8 -*-
import fauxfactory
import pytest

import cfme.configure.configuration as conf
from cfme.base import ZoneCollection
from fixtures.pytest_store import store
from utils.appliance import current_appliance
from utils.update import update


@pytest.mark.tier(1)
@pytest.mark.sauce
@pytest.mark.meta(blockers=[1216224])
def test_zone_crud(soft_assert):
    zc = ZoneCollection(current_appliance)
    # CREATE
    zone = zc.create(
        name=fauxfactory.gen_alphanumeric(5),
        description=fauxfactory.gen_alphanumeric(8)
    )
    soft_assert(zone.exists, "The zone {} does not exist!".format(
        zone.description
    ))
    # UPDATE
    old_desc = zone.description
    with update(zone):
        zone.description = fauxfactory.gen_alphanumeric(8)
    soft_assert(zone.exists and (old_desc != zone.description),
                "The zone {} was not updated!".format(
                    zone.description))
    # DELETE
    zone.delete()
    soft_assert(not zone.exists, "The zone {} exists!".format(
        zone.description
    ))


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_cancel_validation():
    zc = ZoneCollection(current_appliance)
    # CREATE
    zc.create(
        name=fauxfactory.gen_alphanumeric(5),
        description=fauxfactory.gen_alphanumeric(8),
        cancel=True
    )


@pytest.mark.tier(2)
@pytest.mark.sauce
@pytest.mark.meta(blockers=[1216224])
def test_zone_change_appliance_zone(request):
    """ Tests that an appliance can be changed to another Zone """
    zc = ZoneCollection(current_appliance)
    # CREATE
    zone = zc.create(
        name=fauxfactory.gen_alphanumeric(5),
        description=fauxfactory.gen_alphanumeric(8)
    )
    request.addfinalizer(zone.delete)
    request.addfinalizer(conf.BasicInformation(appliance_zone="default").update)
    zone.create()
    basic_info = conf.BasicInformation(appliance_zone=zone.name)
    basic_info.update()
    assert zone.description == store.current_appliance.zone_description
    basic_info = conf.BasicInformation(appliance_zone="default")
    basic_info.update()
