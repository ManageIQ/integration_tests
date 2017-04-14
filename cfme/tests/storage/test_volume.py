# -*- coding: utf-8 -*-
import pytest

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
    view = navigate_to(Volume, 'All')
    assert view.is_displayed

    view = navigate_to(Volume, 'Add')
    assert view.is_displayed

    # grab a volume name, the table returns a generator so use next
    view = navigate_to(Volume, 'All')
    volume_name = view.entities.table.rows().next().name.text
    if not volume_name:
        pytest.skip('Skipping volume navigation for details, could not find configured volume name')

    volume = Volume(name=volume_name, provider=openstack_provider)

    view = navigate_to(volume, 'Details')
    assert view.is_displayed
