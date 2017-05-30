# -*- coding: utf-8 -*-
import pytest
from widgetastic.exceptions import NoSuchElementException

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.storage.volume import Volume

from utils import testgen
from utils.appliance.implementations.ui import navigate_to


pytest_generate_tests = testgen.generate([CloudProvider])


pytestmark = [pytest.mark.tier(3),
              test_requirements.storage,
              pytest.mark.usefixtures('openstack_provider', 'setup_provider')]


@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_volume_navigation(openstack_provider):
    # grab a volume name, the table returns a generator so use next
    view = navigate_to(Volume, 'All')
    try:
        volume_name = view.entities.table[0].name.text
    except (StopIteration, NoSuchElementException):
        pytest.skip('Skipping volume navigation for details, no volumes present')
    volume = Volume(name=volume_name, provider=openstack_provider)

    assert view.is_displayed

    view = navigate_to(volume, 'Details')
    assert view.is_displayed

    view = navigate_to(Volume, 'Add')
    assert view.is_displayed
