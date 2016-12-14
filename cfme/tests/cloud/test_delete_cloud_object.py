# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.cloud.instance.image import Image
from cfme.cloud.provider import CloudProvider
from cfme.cloud.stack import Stack
from cfme.common.vm import VM
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar, Quadicon
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version


pytest_generate_tests = testgen.generate(
    [CloudProvider], required_fields=['remove_test'], scope="module")


pytestmark = [pytest.mark.tier(2),
              test_requirements.general_ui]


@pytest.fixture(scope="module")
def set_grid():
    navigate_to(Image, 'All')
    toolbar.select('Grid View')


def reset():
    navigate_to(Image, 'All')
    toolbar.select('List View')


# TODO take generic object instead of stack when instance and image support navmazing destinations
def refresh_and_wait(provider, stack):
    provider.refresh_provider_relationships()
    navigate_to(stack, 'All')
    if not sel.is_displayed(Quadicon(stack.name, stack.quad_name)):
        stack.wait_for_appear()


def test_delete_instance(setup_provider, provider):
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


def test_delete_image(setup_provider, provider, set_grid, request):
    """ Tests delete image

    Metadata:
        test_flag: delete_object
    """
    # TODO as of 5.6+ clouds_images is no longer in the menu tree
    # Refactor to navigate via clouds instances accordion
    image_name = provider.data['remove_test']['image']
    test_image = VM.factory(image_name, provider, template=True)
    test_image.delete(from_details=False)
    test_image.wait_for_delete()
    provider.refresh_provider_relationships()
    test_image.wait_to_appear()
    request.addfinalizer(reset)


@pytest.mark.uncollectif(lambda: current_version() < "5.4")
def test_delete_stack(setup_provider, provider, provisioning, request):
    """ Tests delete stack

    Metadata:
        test_flag: delete_object
    """
    stack = Stack(provisioning['stack'])
    refresh_and_wait(provider, stack)
    stack.delete()
    navigate_to(stack, 'All')
    assert lambda: not sel.is_displayed(Quadicon(stack.name, stack.quad_name))
