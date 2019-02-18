import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.exceptions import ItemNotFound
from cfme.markers.env_markers.provider import ONE_PER_CATEGORY
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.provider([AzureProvider], selector=ONE_PER_CATEGORY, scope='function'),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture(scope='function')
def map_tags(appliance, provider, request):
    tag = appliance.collections.map_tags.create(entity_type=partial_match(provider.name.title()),
                                                label='test',
                                                category='Testing')
    yield tag
    request.addfinalizer(lambda: tag.delete())


@pytest.fixture(scope='function')
def vm(appliance, provider):
    # cu-24x7 vm is tagged with test:testing in provider
    tag_vm = provider.data.cap_and_util.capandu_vm
    collection = provider.appliance.provider_based_collection(provider)
    try:
        return collection.instantiate(tag_vm, provider)
    except IndexError:
        raise ItemNotFound('VM for tag mapping not found!')


@pytest.fixture(scope='function')
def refresh_provider(provider):
    provider.refresh_provider_relationships()
    wait_for(provider.is_refreshed, func_kwargs={'refresh_delta': 10}, timeout=600)
    return True


@test_requirements.tag
def test_tag_mapping_azure_instances(vm, map_tags, refresh_provider):
    """"
    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/12h
        testSteps:
            1. Find Instance that tagged with test:testing in Azure (cu-24x7)
            2. Create tag mapping for Azure instances
            3. Refresh Provider
            4. Go to Summary of the Instance and read Smart Management field
        expectedResults:
            1.
            2.
            3.
            4. Field value is "My Company Tags Testing: testing"
    """
    view = navigate_to(vm, 'Details')

    def my_company_tags():
        return view.tag.get_text_of('My Company Tags') != 'No My Company Tags have been assigned'
    # sometimes it's not updated immediately after provider refresh
    wait_for(
        my_company_tags,
        timeout=300,
        fail_func=view.toolbar.reload.click
    )
    assert view.tag.get_text_of('My Company Tags')[0] == 'Testing: testing'


@pytest.mark.manual
@pytest.mark.tier(2)
def test_ec2_tags_mapping():
    """
    Requirement: Have an ec2 provider

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/5h
        startsin: 5.8
        testSteps:
            1. Create an instance and tag it with test:testing
            2. Go to Configuration -> CFME Region -> Map Tags
            3. Add a tag:
            Entity: Instance (Amazon)
            Label: test
            Category: Testing
            4. Refresh provider
            5. Go to summary of that instance
            6. In Smart Management field should be:
            My Company Tags testing: Testing
            7. Delete that instance
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_ec2_tags_instances():
    """
    Requirement: Have an ec2 provider

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
        testSteps:
            1. Create an instance with tag test:testing
            2. Refresh provider
            3. Go to summary of this instance and check whether there is
            test:testing in Labels field
            4. Delete that instance
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_ec2_tags_images():
    """
    Requirement: Have an ec2 provider

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
        testSteps:
            1. Select an AMI in AWS console and tag it with test:testing
            2. Refresh provider
            3. Go to summary of this image  and check whether there is
            test:testing in Labels field
            4. Delete that tag
    """
    pass
