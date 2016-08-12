# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import fauxfactory
import pytest

import cfme.web_ui.flash as flash
import cfme.configure.configuration as conf
from utils.update import update
from utils import version


@pytest.mark.tier(1)
@pytest.mark.sauce
@pytest.mark.meta(blockers=[1216224])
@pytest.mark.smoke
def test_zone_crud(soft_assert):
    zone = conf.Zone(
        name=fauxfactory.gen_alphanumeric(5),
        description=fauxfactory.gen_alphanumeric(8))
    # CREATE
    zone.create()
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
    zone = conf.Zone(
        name=fauxfactory.gen_alphanumeric(5),
        description=fauxfactory.gen_alphanumeric(8))
    zone.create(cancel=True)
    if version.current_version() >= 5.6:
        msg = 'Add of new Zone was cancelled by the user'
    else:
        msg = 'Add of new Miq Zone was cancelled by the user'
    flash.assert_message_match(msg)


@pytest.mark.tier(2)
@pytest.mark.sauce
@pytest.mark.meta(blockers=[1216224])
def test_zone_change_appliance_zone(request):
    """ Tests that an appliance can be changed to another Zone """
    zone = conf.Zone(
        name=fauxfactory.gen_alphanumeric(5),
        description=fauxfactory.gen_alphanumeric(8))
    request.addfinalizer(zone.delete)
    request.addfinalizer(conf.BasicInformation(appliance_zone="default").update)
    zone.create()
    basic_info = conf.BasicInformation(appliance_zone=zone.name)
    basic_info.update()
    assert zone.description == conf.server_zone_description()
    basic_info = conf.BasicInformation(appliance_zone="default")
    basic_info.update()
