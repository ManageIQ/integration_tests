# -*- coding: utf-8 -*-

import pytest
from cfme import test_requirements
from cfme.configure.settings import visual
from cfme.fixtures import pytest_selenium as sel
from cfme.utils.appliance import current_appliance
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.configure import settings  # NOQA


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


@pytest.yield_fixture(scope="module")
def set_timezone():
    time_zone = visual.timezone
    visual.timezone = "(GMT-10:00) Hawaii"
    yield
    visual.timezone = time_zone


def test_timezone_setting(set_timezone):
    """ Tests  timezone setting

    Metadata:
        test_flag: visuals
    """
    locator = ('//label[contains(@class,"control-label") and contains(., "Started On")]'
               '/../div/p[contains(., "{}")]'.format("-1000"))

    navigate_to(current_appliance.server, 'DiagnosticsDetails')

    assert sel.is_displayed(locator), "Timezone settings Failed"
