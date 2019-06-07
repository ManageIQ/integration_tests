# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.appliance import current_appliance
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update


pytestmark = [test_requirements.configuration]


@pytest.mark.tier(1)
@pytest.mark.sauce
@pytest.mark.meta(blockers=[1216224])
def test_zone_crud(soft_assert):
    """
    Polarion:
        assignee: tpapaioa
        caseimportance: low
        initialEstimate: 1/15h
        casecomponent: WebUI
    """
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
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/20h
    """
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
    """ Tests that an appliance can be changed to another Zone

    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/15h
    """
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
def test_zone_add_dupe(appliance, request):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/4h
    """
    zc = current_appliance.collections.zones
    name = fauxfactory.gen_alphanumeric(5)
    description = fauxfactory.gen_alphanumeric(8)
    zone = zc.create(
        name=name,
        description=description)
    request.addfinalizer(zone.delete)

    with pytest.raises(
        Exception,
        match="Name is not unique within region {}".format(appliance.server.zone.region.number)
    ):
        zc.create(
            name=name,
            description=description)


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_maxlength(request, soft_assert):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/4h
    """
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
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
    """
    zc = current_appliance.collections.zones
    with pytest.raises(Exception, match="Name can't be blank"):
        zc.create(
            name='',
            description=fauxfactory.gen_alphanumeric(8)
        )


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_blank_description():
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
    """
    zc = current_appliance.collections.zones
    with pytest.raises(Exception, match="Description can't be blank"):
        zc.create(
            name=fauxfactory.gen_alphanumeric(5),
            description=''
        )


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_add_zone_windows_domain_credentials(request):
    """
    Testing Windows Domain credentials add

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    zc = current_appliance.collections.zones.all()
    values = {'username': 'userid',
              'password': 'password',
              'verify': 'password'}
    zc[0].update(values)

    def _cleanup():
        remove_values = {'username': '',
                         'password': '',
                         'verify': ''}
        zc[0].update(remove_values)

    request.addfinalizer(_cleanup)
    view = navigate_to(zc[0], 'Edit')
    zc_username = view.username.read()
    assert zc_username == values['username'], "Current username is {}".format(zc_username)


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_remove_zone_windows_domain_credentials():
    """
    Testing Windows Domain credentials removal

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    zc = current_appliance.collections.zones.all()
    values = {'username': 'userid',
              'password': 'password',
              'verify': 'password'}
    zc[0].update(values)
    view = navigate_to(zc[0], 'Edit')
    zc_username = view.username.read()
    assert zc_username == values['username'], "Username wasn't updated"
    remove_values = {'username': '',
                     'password': '',
                     'verify': ''}
    zc[0].update(remove_values)
    view = navigate_to(zc[0], 'Edit')
    removed_zc_username = view.username.read()
    assert removed_zc_username == remove_values['username'], "Username wasn't removed"
