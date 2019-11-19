import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.ui import ZoneAddView
from cfme.exceptions import ItemNotFound
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update


pytestmark = [test_requirements.configuration]

NAME_LEN = 5
DESC_LEN = 8


# Finalizer method that clicks Cancel for tests that expect zone
# creation to fail. This avoids logging of UnexpectedAlertPresentException
# for the 'Abandon changes?' alert when the next test tries to navigate
# elsewhere in the UI.
def cancel_zone_add(appliance):
    view = appliance.browser.create_view(ZoneAddView)
    if view.is_displayed:
        view.cancel_button.click()


def create_zone(appliance, name_len=NAME_LEN, desc_len=DESC_LEN):
    zc = appliance.collections.zones
    region = appliance.server.zone.region

    # CREATE
    name = fauxfactory.gen_alphanumeric(name_len)
    description = fauxfactory.gen_alphanumeric(desc_len)
    zc.create(name=name, description=description)

    # query to get the newly-created zone's id
    zc.filters = {'parent': region}
    zones = zc.all()
    new_zone = None
    for zone in zones:
        if (zone.name == name and zone.description == description):
            new_zone = zone
            break
    else:
        pytest.fail(
            f'Zone matching name ({name}) and \
            description ({description}) not found in the collection')

    return new_zone


@pytest.mark.tier(1)
@pytest.mark.sauce
def test_zone_crud(appliance):
    """
    Bugzilla:
        1216224

    Polarion:
        assignee: tpapaioa
        caseimportance: low
        initialEstimate: 1/15h
        casecomponent: WebUI
    """
    zone = create_zone(appliance)
    assert zone.exists, 'Zone could not be created.'

    # UPDATE
    with update(zone):
        zone.description = f'{zone.description}_updated'

    try:
        navigate_to(zone, 'Zone')
    except ItemNotFound:
        pytest.fail(f'Zone {zone.description} could not be updated.')

    # DELETE
    zone.delete()
    assert (not zone.exists), f'Zone {zone.description} could not be deleted.'


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_cancel_validation(appliance):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/20h
    """
    appliance.collections.zones.create(
        name=fauxfactory.gen_alphanumeric(NAME_LEN),
        description=fauxfactory.gen_alphanumeric(DESC_LEN),
        cancel=True
    )


@pytest.mark.tier(2)
@pytest.mark.sauce
def test_zone_change_appliance_zone(request, appliance):
    """ Tests that an appliance can be changed to another Zone
    Bugzilla:
        1216224

    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/15h
    """
    zone = create_zone(appliance)
    request.addfinalizer(zone.delete)

    server_settings = appliance.server.settings
    request.addfinalizer(lambda: server_settings.update_basic_information(
        {'appliance_zone': 'default'}))

    server_settings.update_basic_information({'appliance_zone': zone.name})
    assert (zone.description == appliance.server.zone.description)


@pytest.mark.tier(2)
@pytest.mark.sauce
def test_zone_add_dupe(request, appliance):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/4h
    """
    zone = create_zone(appliance)
    request.addfinalizer(zone.delete)

    request.addfinalizer(lambda: cancel_zone_add(appliance))
    with pytest.raises(
        Exception,
        match=f'Name is not unique within region {appliance.server.zone.region.number}'
    ):
        appliance.collections.zones.create(
            name=zone.name,
            description=zone.description
        )


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_maxlength(request, appliance):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/4h
    """
    zone = create_zone(appliance, name_len=50, desc_len=50)
    request.addfinalizer(zone.delete)
    assert zone.exists, f'Zone does not exist.'


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_blank_name(request, appliance):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
    """
    request.addfinalizer(lambda: cancel_zone_add(appliance))
    with pytest.raises(Exception, match="Name can't be blank"):
        appliance.collections.zones.create(
            name='',
            description=fauxfactory.gen_alphanumeric(DESC_LEN)
        )


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_blank_description(request, appliance):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
    """
    request.addfinalizer(lambda: cancel_zone_add(appliance))
    with pytest.raises(Exception, match=r"(Description can't be blank|Description is required)"):
        appliance.collections.zones.create(
            name=fauxfactory.gen_alphanumeric(NAME_LEN),
            description=''
        )


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_add_zone_windows_domain_credentials(request, appliance):
    """
    Testing Windows Domain credentials add

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    zone = appliance.collections.zones.all()[0]
    values = {'username': 'userid',
              'password': 'password',
              'verify': 'password'}
    zone.update(values)

    def _cleanup():
        values = {'username': '',
                  'password': '',
                  'verify': ''}
        zone.update(values)

    request.addfinalizer(_cleanup)
    view = navigate_to(zone, 'Edit')
    username = view.username.read()
    assert username == values['username'], f'Current username is {username}'


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_remove_zone_windows_domain_credentials(appliance):
    """
    Testing Windows Domain credentials removal

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    zone = appliance.collections.zones.all()[0]
    values = {'username': 'userid',
              'password': 'password',
              'verify': 'password'}
    zone.update(values)

    view = navigate_to(zone, 'Edit')
    username = view.username.read()
    assert username == values['username'], "Username wasn't updated"

    values = {'username': '',
              'password': '',
              'verify': ''}
    zone.update(values)

    view = navigate_to(zone, 'Edit')
    username = view.username.read()
    assert username == values['username'], "Username wasn't removed"
