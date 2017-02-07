# -*- coding: utf-8 -*-
import fauxfactory
import pytest

import cfme.configure.configuration as conf
from cfme.base import ZoneCollection
from fixtures.pytest_store import store
from utils.appliance import current_appliance
from utils.update import update
import utils.error as error


@pytest.mark.tier(1)
@pytest.mark.sauce
@pytest.mark.meta(blockers=[1216224])
def test_zone_crud(soft_assert):
    zc = current_appliance.get(ZoneCollection)
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
    zc = current_appliance.get(ZoneCollection)
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
    zc = current_appliance.get(ZoneCollection)
    # CREATE
    zone = zc.create(
        name=fauxfactory.gen_alphanumeric(5),
        description=fauxfactory.gen_alphanumeric(8)
    )
    request.addfinalizer(zone.delete)

    @request.addfinalizer
    def _return_zone_back():
        current_appliance.server.zone = current_appliance.default_zone
    request.addfinalizer(conf.BasicInformation(appliance_zone="default").update)
    basic_info = conf.BasicInformation(appliance_zone=zone.name)
    basic_info.update()
    current_appliance.server.zone = zone
    assert zone.description == store.current_appliance.zone_description


@pytest.mark.tier(2)
@pytest.mark.sauce
def test_zone_add_dupe(request):
    zc = ZoneCollection(current_appliance)
    name = fauxfactory.gen_alphanumeric(5)
    description = fauxfactory.gen_alphanumeric(8)
    zone = zc.create(
        name=name,
        description=description)
    request.addfinalizer(zone.delete)

    with error.expected('Name has already been taken'):
        zc.create(
            name=name,
            description=description)


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_maxlength(request, soft_assert):
    zc = ZoneCollection(current_appliance)
    zone = zc.create(
        name=fauxfactory.gen_alphanumeric(50),
        description=fauxfactory.gen_alphanumeric(50)
    )
    request.addfinalizer(zone.delete)
    soft_assert(zone.exists, "The zone {} does not exist!".format(
        zone.description
    ))


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_blank_name():
    zc = ZoneCollection(current_appliance)
    with error.expected("Name can't be blank"):
        zc.create(
            name='',
            description=fauxfactory.gen_alphanumeric(8)
        )


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_blank_description():
    zc = ZoneCollection(current_appliance)
    with error.expected("Description is required"):
        zc.create(
            name=fauxfactory.gen_alphanumeric(5),
            description=''
        )
