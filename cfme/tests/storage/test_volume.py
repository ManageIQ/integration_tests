# -*- coding: utf-8 -*-
import pytest

from cfme.exceptions import ItemNotFound
from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.openstack import OpenStackProvider

from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to


pytest_generate_tests = testgen.generate([CloudProvider])


pytestmark = [pytest.mark.tier(3),
              test_requirements.storage,
              pytest.mark.usefixtures('openstack_provider', 'setup_provider')]


@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_volume_navigation(openstack_provider, appliance):
    # grab a volume name, the table returns a generator so use next

    collection = appliance.collections.volumes
    view = navigate_to(collection, 'All')

    try:
        volume_name = view.entities.get_first_entity().name
    except(StopIteration, ItemNotFound):
        pytest.skip('Skipping volume navigation for details, no volumes present')

    volume = collection.instantiate(name=volume_name, provider=openstack_provider)

    assert view.is_displayed

    view = navigate_to(volume, 'Details')
    assert view.is_displayed

    view = navigate_to(collection, 'Add')
    assert view.is_displayed


@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_volume_collective_crud(openstack_provider, appliance):
    collection = appliance.collections.volumes
    view = navigate_to(collection, 'All')

    volumes = [collection.instantiate(name=item.name, provider=openstack_provider)
              for item in view.entities.get_all()]

    if volumes:
        collection.delete(*volumes)
    else:
        pytest.skip("Skipping volume collective deletion, no volumes present")
