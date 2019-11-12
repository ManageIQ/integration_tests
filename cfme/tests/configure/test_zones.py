import fauxfactory
import pytest

from cfme import test_requirements
from cfme.exceptions import ItemNotFound
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update


pytestmark = [test_requirements.configuration]


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
    zc = appliance.collections.zones
    region = appliance.server.zone.region

    # CREATE
    name = fauxfactory.gen_alphanumeric(5)
    description = fauxfactory.gen_alphanumeric(8)
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

    assert new_zone.exists, f'Zone {description} could not be created.'

    # UPDATE
    with update(new_zone):
        new_zone.description = f'{description}_updated'

    try:
        navigate_to(new_zone, 'Zone')
    except ItemNotFound:
        pytest.fail(f'Zone {new_zone.description} could not be updated.')

    # DELETE
    new_zone.delete()
    assert (not new_zone.exists), f'Zone {new_zone.description} could not be deleted.'


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
    zc = appliance.collections.zones
    # CREATE
    zc.create(
        name=fauxfactory.gen_alphanumeric(5),
        description=fauxfactory.gen_alphanumeric(8),
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
    zc = appliance.collections.zones
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
    assert (zone.description == appliance.server.zone.description)


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
    zc = appliance.collections.zones
    name = fauxfactory.gen_alphanumeric(5)
    description = fauxfactory.gen_alphanumeric(8)
    zone = zc.create(
        name=name,
        description=description)
    request.addfinalizer(zone.delete)

    with pytest.raises(
        Exception,
        match=f'Name is not unique within region {appliance.server.zone.region.number}'
    ):
        zc.create(
            name=name,
            description=description)


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
    zc = appliance.collections.zones
    zone = zc.create(
        name=fauxfactory.gen_alphanumeric(50),
        description=fauxfactory.gen_alphanumeric(50)
    )
    request.addfinalizer(zone.delete)
    assert zone.exists, f'The zone {zone.description} does not exist.'


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_blank_name(appliance):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
    """
    zc = appliance.collections.zones
    with pytest.raises(Exception, match="Name can't be blank"):
        zc.create(
            name='',
            description=fauxfactory.gen_alphanumeric(8)
        )


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_blank_description(appliance):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
    """
    zc = appliance.collections.zones
    with pytest.raises(Exception, match=r"(Description can't be blank|Description is required)"):
        zc.create(
            name=fauxfactory.gen_alphanumeric(5),
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
    zc = appliance.collections.zones.all()
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
    assert zc_username == values['username'], f'Current username is {zc_username}'


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
    zc = appliance.collections.zones.all()
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
