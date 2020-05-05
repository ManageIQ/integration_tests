import pytest

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.providers import list_providers_by_class


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.storage,
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([EC2Provider, OpenStackProvider], scope="module"),
]


def assert_volume_type_should_be_present(block_manager, should_be_present):
    view = navigate_to(block_manager, 'Details')
    block_storage_manager_relationship_fields = view.entities.relationships.fields
    assert (
        ('Cloud Volume Types' in block_storage_manager_relationship_fields) == should_be_present)


@pytest.mark.meta(automates=[1650082], blockers=[
    BZ(1650082, forced_streams=["5.11", "5.10"],
       unblock=lambda provider: not provider.one_of(OpenStackProvider))])
def test_storage_volume_type_present(appliance, provider, request):
    """
    Bugzilla:
        1650082
    Polarion:
        assignee: mmojzis
        caseimportance: medium
        initialEstimate: 1/4h
        casecomponent: Cloud
        testSteps:
            1. Add EC2 Provider
            2. Check EBS Block Storage Manager Details
            3. Add Openstack Provider
            4. Check EBS Block Storage Details
            5. Check Cinder Storage Manager Details
            6. Delete EC2 Provider
            7. Check Cinder Storage Manager Details
        expectedResults:
            1.
            2. There are not Cloud Volume Types present in the details
            3.
            4. There are not Cloud Volume Types present in the details
            5. There are Cloud Volume Types present in the details
            6.
            7. There are Cloud Volume Types present in the details
    """
    should_be_present = False
    other_provider = list_providers_by_class(OpenStackProvider)[0]
    if provider.one_of(OpenStackProvider):
        other_provider = list_providers_by_class(EC2Provider)[0]
        should_be_present = True

    # check with provider added only
    block_manager, = appliance.collections.block_managers.filter({"provider": provider}).all()
    assert_volume_type_should_be_present(block_manager, should_be_present)

    # check also with other provider class that should have opposite result for volume_type_present
    other_provider.create(validate_inventory=True)
    request.addfinalizer(lambda: provider.delete_if_exists())
    assert_volume_type_should_be_present(block_manager, should_be_present)
