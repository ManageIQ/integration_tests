import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.ui import ZoneAddView
from cfme.exceptions import ItemNotFound
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.update import update


pytestmark = [test_requirements.configuration]

NAME_LEN = 5
DESC_LEN = 8


def cancel_zone_add(appliance):
    """Finalizer method that clicks Cancel for tests that expect zone creation to fail.
    This avoids logging of UnexpectedAlertPresentException for the 'Abandon changes?' alert
    when the next test tries to navigate elsewhere in the UI."""

    view = appliance.browser.create_view(ZoneAddView)
    if view.is_displayed:
        view.cancel_button.click()


def create_zone(appliance, name, desc):
    """Create zone with the given name and description.

    Returns: :py:class:`cfme.base.Zone` object
    """
    zc = appliance.collections.zones
    region = appliance.server.zone.region
    zc.create(name=name, description=desc)

    # Re-instantiate the Zone object, to get the id.
    zc.filters = {'parent': region}
    zones = zc.all()
    new_zone = None
    for zone in zones:
        if zone.name == name and zone.description == desc:
            new_zone = zone
            break
    else:
        pytest.fail(
            f"Zone with name {name!r} and description {desc!r} "
            "not found in the collection.")

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
    name = fauxfactory.gen_string('alphanumeric', NAME_LEN)
    desc = fauxfactory.gen_string('alphanumeric', DESC_LEN)

    zone = create_zone(appliance, name, desc)
    assert zone.exists, (
        f"Zone could not be created with name {name} "
        f"and description {desc}.")

    # UPDATE
    new_desc = f'{zone.description}_updated'
    with update(zone):
        zone.description = new_desc
    try:
        navigate_to(zone, 'Zone')
    except ItemNotFound:
        pytest.fail("Zone description could not be updated."
            f" Expected: {new_desc}."
            f" Current: {zone.description}.")

    # DELETE
    zone.delete()
    assert not zone.exists, f"Zone {zone.description} could not be deleted."


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
    name = fauxfactory.gen_string('alphanumeric', NAME_LEN)
    desc = fauxfactory.gen_string('alphanumeric', DESC_LEN)

    appliance.collections.zones.create(
        name=name,
        description=desc,
        cancel=True
    )


@pytest.mark.tier(2)
@pytest.mark.sauce
def test_zone_change_appliance_zone(request, appliance):
    """Test that an appliance can be assigned to another zone.
    Bugzilla:
        1216224

    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/15h
    """
    name = fauxfactory.gen_string('alphanumeric', NAME_LEN)
    desc = fauxfactory.gen_string('alphanumeric', DESC_LEN)
    zone = create_zone(appliance, name, desc)
    request.addfinalizer(zone.delete)

    server_settings = appliance.server.settings
    request.addfinalizer(lambda: server_settings.update_basic_information(
        {'appliance_zone': 'default'}))

    server_settings.update_basic_information({'appliance_zone': zone.name})
    assert (zone.description == appliance.server.zone.description)


@pytest.mark.tier(2)
@pytest.mark.sauce
def test_zone_add_duplicate(request, appliance):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/4h
    """
    name = fauxfactory.gen_string('alphanumeric', NAME_LEN)
    desc = fauxfactory.gen_string('alphanumeric', DESC_LEN)

    zone = create_zone(appliance, name, desc)
    assert zone.exists, (
        f"Zone could not be created with name {name} and description {desc}.")
    request.addfinalizer(zone.delete)

    request.addfinalizer(lambda: cancel_zone_add(appliance))
    with pytest.raises(
        Exception,
        match=f"Name is not unique within region {appliance.server.zone.region.number}"
    ):
        create_zone(appliance, name, desc)


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
    name = fauxfactory.gen_string('alphanumeric', 50)
    desc = fauxfactory.gen_string('alphanumeric', 50)
    zone = create_zone(appliance, name, desc)
    request.addfinalizer(zone.delete)
    assert zone.exists, "Zone does not exist."


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_zone_add_punctuation(request, appliance):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/4h
    """
    name = fauxfactory.gen_string('punctuation', NAME_LEN)
    desc = fauxfactory.gen_string('punctuation', DESC_LEN)
    zone = create_zone(appliance, name, desc)
    request.addfinalizer(zone.delete)
    assert zone.exists, "Zone does not exist."


@pytest.mark.tier(3)
@pytest.mark.sauce
@pytest.mark.meta(blockers=[BZ(1797715, forced_streams=["5.10", "5.11"])])
def test_zone_add_whitespace(request, appliance):
    """When creating a new zone, the name can have whitespace, including leading and trailing
    characters. After saving, the whitespace should be displayed correctly in the web UI.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/30h
    """
    name = "    " + fauxfactory.gen_string('alphanumeric', 5)
    desc = "    " + fauxfactory.gen_string('alphanumeric', 8)
    zone = create_zone(appliance, name, desc)
    request.addfinalizer(zone.delete)
    assert zone.exists, (f"Zone with name {name} and description {desc}"
                         "could not be found in the UI.")


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
    name = ''
    desc = fauxfactory.gen_string('alphanumeric', DESC_LEN)
    request.addfinalizer(lambda: cancel_zone_add(appliance))
    with pytest.raises(Exception, match="Name can't be blank"):
        create_zone(appliance, name, desc)


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
    name = fauxfactory.gen_string('alphanumeric', NAME_LEN)
    desc = ''
    request.addfinalizer(lambda: cancel_zone_add(appliance))
    with pytest.raises(Exception, match=r"(Description can't be blank|Description is required)"):
        create_zone(appliance, name, desc)


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
