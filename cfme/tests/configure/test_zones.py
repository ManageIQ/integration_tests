# -*- coding: utf-8 -*-
import pytest

import cfme.web_ui.flash as flash
import cfme.configure.configuration as conf
from utils import testgen
from utils.randomness import generate_random_string
from utils.update import update


def test_zone_create(request):
    """ Tests that a Zone can be created """
    zone = conf.Zone(
        name=generate_random_string(size=5),
        description=generate_random_string(size=8))
    zone.create()
    request.addfinalizer(zone.delete)
    flash.assert_message_match('Zone "%s" was added' % zone.details["name"])


def test_zone_delete():
    """ Tests that a Zone can be deleted """
    zone = conf.Zone(
        name=generate_random_string(size=6),
        description=generate_random_string(size=8))
    zone.create()
    flash.assert_message_match('Zone "%s" was added' % zone.details["name"])
    zone.delete()
    flash.assert_message_match('Zone "%s": Delete successful' % zone.details["name"])


def test_zone_edit(request):
    """ Tests that a Zone's description can be updated """
    zone = conf.Zone(
        name=generate_random_string(size=5),
        description=generate_random_string(size=8))
    zone.create()
    request.addfinalizer(zone.delete)
    olddesc = zone.details["description"]
    with update(zone):
        zone.details["description"] = generate_random_string(size=8)
    flash.assert_message_match('Zone "%s" was saved' % zone.details["name"])

    with update(zone):
        zone.details["description"] = olddesc
    flash.assert_message_match('Zone "%s" was saved' % zone.details["name"])
