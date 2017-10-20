# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.cloud.instance.image import Image
from cfme.cloud.provider import CloudProvider
from cfme.cloud.stack import StackCollection
from cfme.common.vm import VM
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import TimedOutError

pytestmark = [
    pytest.mark.tier(2),
    test_requirements.general_ui,
    pytest.mark.provider([CloudProvider], required_fields=['remove_test'], scope="module")
]


@pytest.fixture(scope="module")
def set_grid():
    view = navigate_to(Image, 'All')
    view.toolbar.view_selector.select('Grid View')


def reset():
    view = navigate_to(Image, 'All')
    view.toolbar.view_selector.select('List View')


def test_delete_instance_appear_after_refresh(setup_provider, provider):
    """ Tests delete instance

    Metadata:
        test_flag: delete_object
    """
    instance_name = provider.data['remove_test']['instance']
    test_instance = VM.factory(instance_name, provider)
    test_instance.delete(from_details=False)
    test_instance.wait_for_delete()
    provider.refresh_provider_relationships()
    test_instance.wait_to_appear()


def test_delete_image_appear_after_refresh(setup_provider, provider, set_grid, request):
    """ Tests delete image

    Metadata:
        test_flag: delete_object
    """
    image_name = provider.data['remove_test']['image']
    test_image = VM.factory(image_name, provider, template=True)
    test_image.delete(from_details=False)
    test_image.wait_for_delete()
    provider.refresh_provider_relationships()
    test_image.wait_to_appear()
    request.addfinalizer(reset)


def test_delete_stack_appear_after_refresh(setup_provider, provider, provisioning, request,
                                           appliance):
    """ Tests delete stack

    Metadata:
        test_flag: delete_object
    """

    stack = StackCollection(appliance).instantiate(name=provisioning['stacks'][0],
                                                   provider=provider)
    # wait for delete implemented in delete()
    stack.delete()
    # refresh relationships is implemented in wait_for_exists()
    try:
        stack.wait_for_exists()
    except TimedOutError:
        pytest.fail("stack didn't appear after refresh")
    request.addfinalizer(reset)
