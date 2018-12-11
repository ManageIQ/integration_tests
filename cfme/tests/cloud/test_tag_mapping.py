import pytest

from cfme.cloud.provider.azure import AzureProvider
from cfme.exceptions import ItemNotFound
from cfme.markers.env_markers.provider import ONE_PER_CATEGORY
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for

from widgetastic.utils import partial_match

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


def test_tag_mapping_azure_instances(vm, map_tags, refresh_provider):
    """"
    1. Find Instance that tagged with test:testing in Azure (cu-24x7)
    2. Create tag mapping for Azure instances
    3. Refresh Provider
    4. Go to Summary of the Instance
    Expected result: In Smart Management field should be:
    My Company Tags Testing: testing

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        caseimportance: high
        initialEstimate: 1/12h
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
