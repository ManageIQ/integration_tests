import random
import pytest

from cfme.containers.provider import ContainersProvider

pytestmark = [
    pytest.mark.meta(server_roles='+smartproxy'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')]


@pytest.fixture(scope='function')
def random_image_instance(appliance):
    collection = appliance.collections.container_images
    return random.sample(collection.all(), 1).pop()


@pytest.mark.polarion('10068')
def test_check_compliance_provider_policy(provider, random_image_instance):
    # unassign OpenSCAP policy from chosen Image
    random_image_instance.unassign_policy_profiles('OpenSCAP profile')

    # assign policy from provider view
    provider.assign_policy_profiles('OpenSCAP profile')

    # check Image compliance
    random_image_instance.check_compliance()

    # unassign OpenSCAP policy from provider view
    provider.unassign_policy_profiles('OpenSCAP profile')
