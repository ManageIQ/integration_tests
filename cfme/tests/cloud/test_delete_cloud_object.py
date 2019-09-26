# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import TimedOutError

pytestmark = [
    pytest.mark.tier(2),
    test_requirements.cloud,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([CloudProvider], required_fields=['remove_test'], scope="module")
]


@pytest.fixture()
def set_grid(appliance):
    view = navigate_to(appliance.collections.cloud_images, 'All')
    view.toolbar.view_selector.select('Grid View')
    yield
    view = navigate_to(appliance.collections.cloud_images, 'All')
    view.toolbar.view_selector.select('List View')


def test_delete_instance_appear_after_refresh(appliance, provider):
    """ Tests delete instance

    Metadata:
        test_flag: delete_object

    Polarion:
        assignee: mmojzis
        casecomponent: WebUI
        initialEstimate: 1/4h
    """
    instance_name = provider.data['remove_test']['instance']
    test_instance = appliance.collections.cloud_instances.instantiate(instance_name, provider)
    test_instance.delete(from_details=False)
    test_instance.wait_for_delete()
    provider.refresh_provider_relationships()
    test_instance.wait_to_appear()


def test_delete_image_appear_after_refresh(appliance, provider, set_grid, request):
    """ Tests delete image

    Metadata:
        test_flag: delete_object

    Polarion:
        assignee: mmojzis
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    """
    image_name = provider.data['remove_test']['image']
    test_image = appliance.collections.cloud_images.instantiate(image_name, provider)
    test_image.delete(from_details=False)
    test_image.wait_for_delete()
    provider.refresh_provider_relationships()
    test_image.wait_to_appear()


def test_delete_stack_appear_after_refresh(appliance, provider, provisioning,
                                           request):
    """ Tests delete stack

    Metadata:
        test_flag: delete_object

    Polarion:
        assignee: mmojzis
        casecomponent: WebUI
        initialEstimate: 1/4h
    """

    stack = appliance.collections.cloud_stacks.instantiate(name=provisioning['stacks'][0],
                                                           provider=provider)
    # wait for delete implemented in delete()
    stack.delete()
    # refresh relationships is implemented in wait_for_exists()
    try:
        stack.wait_for_exists()
    except TimedOutError:
        pytest.fail("stack didn't appear after refresh")
