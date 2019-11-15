from collections import namedtuple

import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to


TimeZone = namedtuple('TimeZone', ['friendly', 'machine'])

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings]

colors = [
    'Orange',
    'Yellow',
    'Green',
    'Blue',
    'ManageIQ-Blue',
    'Black',
]
test_timezone = TimeZone(friendly='(GMT-10:00) Hawaii', machine='-1000')


@pytest.fixture(scope='module')
def set_timezone(appliance):
    old_time_zone = appliance.user.my_settings.visual.timezone
    appliance.user.my_settings.visual.timezone = test_timezone.friendly
    yield
    appliance.user.my_settings.visual.timezone = old_time_zone


def test_timezone_setting(appliance, set_timezone):
    """ Tests  timezone setting

    Metadata:
        test_flag: visuals

    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/30h
    """
    view = navigate_to(appliance.server, 'DiagnosticsDetails')
    assert test_timezone.machine in view.summary.started_on.text, 'Timezone settings Failed'
