# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.utils import error
from cfme.utils.appliance import current_appliance
from cfme.utils.update import update


@pytest.mark.tier(1)
@pytest.mark.sauce
@pytest.mark.meta(blockers=[1216224])
def test_zone_crud(soft_assert):
    zc = current_appliance.collections.zones
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
    zc = current_appliance.collections.zones
    # CREATE
    zc.create(
        name=fauxfactory.gen_alphanumeric(5),
        description=fauxfactory.gen_alphanumeric(8),
        cancel=True
    )


@pytest.mark.tier(2)
@pytest.mark.sauce
@pytest.mark.meta(blockers=[1216224])
def test_zone_change_appliance_zone(request, appliance):
    """ Tests that an appliance can be changed to another Zone """
    zc = current_appliance.collections.zones
    # CREATE
    zone = zc.create(
        name=fauxfactory.gen_alphanumeric(5),
        description=fauxfactory.gen_alphanumeric(8)
    )
    request.addfinalizer(zone.delete)

    server_settings = appliance.server.settings
    request.addfinalizer(lambda: server_settings.update_basic_information(
        {'appliance_zone': "default"}))
    server_settings.update_basic_information({'appliance_zone': zone.name})
    assert zone.description == appliance.server.zone.description


@pytest.mark.tier(2)
@pytest.mark.sauce
def test_zone_add_dupe(request):
    zc = current_appliance.collections.zones
    name = fauxfactory.gen_alphanumeric(5)
    description = fauxfactory.gen_alphanumeric(8)
    zone = zc.create(
        name=name,
        description=description)
    request.addfinalizer(zone.delete)

    if current_appliance.version >= 5.9:
        error_flash = "Name is not unique within region 0"
    else:
        error_flash = "Name has already been taken"
    with error.expected(error_flash):
        zc.create(
            name=name,
            description=description)


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_maxlength(request, soft_assert):
    zc = current_appliance.collections.zones
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
    zc = current_appliance.collections.zones
    with error.expected("Name can't be blank"):
        zc.create(
            name='',
            description=fauxfactory.gen_alphanumeric(8)
        )


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_blank_description():
    zc = current_appliance.collections.zones
    with error.expected("Description is required"):
        zc.create(
            name=fauxfactory.gen_alphanumeric(5),
            description=''
        )
