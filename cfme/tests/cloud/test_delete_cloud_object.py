# -*- coding: utf-8 -*-

from cfme.fixtures import pytest_selenium as sel
from cfme.cloud import stack
from cfme.common.vm import VM
from cfme.web_ui import toolbar
from utils import testgen
from utils.version import current_version
import pytest


def pytest_generate_tests(metafunc):
    # Filter out providers without templates defined
    argnames, argvalues, idlist = testgen.cloud_providers(metafunc, required_fields=['remove_test'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope="module")
def set_grid():
    sel.force_navigate("clouds_images")
    toolbar.select('Grid View')


@pytest.fixture(scope="module")
def set_grid_stack():
    sel.force_navigate("clouds_stacks")
    toolbar.select('Grid View')


def reset():
    sel.force_navigate("clouds_images")
    toolbar.select('List View')


def reset_grid_stack():
    sel.force_navigate("clouds_stacks")
    toolbar.select('List View')


def test_delete_instance(setup_provider, provider):
    """ Tests delete instance

    Metadata:
        test_flag: delete_object
    """
    instance_name = provider.data['remove_test']['instance']
    test_instance = VM.factory(instance_name, provider)
    test_instance.delete()
    test_instance.wait_for_delete()
    provider.refresh_provider_relationships()
    test_instance.wait_to_appear()


def test_delete_image(setup_provider, provider, set_grid, request):
    """ Tests delete image

    Metadata:
        test_flag: delete_object
    """
    image_name = provider.data['remove_test']['image']
    test_image = VM.factory(image_name, provider, template=True)
    test_image.delete()
    test_image.wait_for_delete()
    provider.refresh_provider_relationships()
    test_image.wait_to_appear()
    request.addfinalizer(reset)


@pytest.mark.uncollectif(lambda: current_version() < "5.4")
def test_delete_stack(setup_provider, provider, set_grid_stack, request):
    """ Tests delete stack

    Metadata:
        test_flag: delete_object
    """
    stack_name = provider.data['remove_test']['stack']
    test_stack = stack.Stack(stack_name)
    test_stack.delete()
    test_stack.wait_for_delete()
    provider.refresh_provider_relationships()
    test_stack.wait_for_appear()
    request.addfinalizer(reset_grid_stack)
