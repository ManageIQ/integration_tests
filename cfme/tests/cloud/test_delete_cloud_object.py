# -*- coding: utf-8 -*-

from cfme.fixtures import pytest_selenium as sel
from cfme.cloud import instance, stack
from cfme.web_ui import Region, toolbar
from utils.version import current_version
from utils import testgen
import pytest


# Page specific locators
details_page = Region(infoblock_type='detail')


def pytest_generate_tests(metafunc):
    # Filter out providers without templates defined
    argnames, argvalues, idlist = testgen.cloud_providers(metafunc, 'remove_test')
    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['remove_test']:
            # Don't know what type of instance to provision, move on
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def set_grid():
    sel.force_navigate("clouds_images")
    toolbar.set_vms_grid_view()


@pytest.fixture(scope="module")
def set_grid_stack():
    sel.force_navigate("clouds_stacks")
    toolbar.set_vms_grid_view()


def reset():
    sel.force_navigate("clouds_images")
    toolbar.set_vms_list_view()


def reset_grid_stack():
    sel.force_navigate("clouds_stacks")
    toolbar.set_vms_list_view()


def test_delete_instance(setup_provider, provider, remove_test):
    """ Tests delete instance

    Metadata:
        test_flag: delete_object
    """
    instance_name = remove_test['instance']
    test_instance = instance.instance_factory(instance_name, provider)
    test_instance.remove_from_cfme(cancel=False)
    test_instance.wait_for_delete()
    provider.refresh_provider_relationships()
    test_instance.wait_for_vm_to_appear()


def test_delete_image(setup_provider, provider, remove_test, set_grid, request):
    """ Tests delete image

    Metadata:
        test_flag: delete_object
    """
    image_name = remove_test['image']
    test_image = instance.Image(image_name, provider)
    test_image.delete()
    test_image.wait_for_delete()
    provider.refresh_provider_relationships()
    test_image.wait_for_appear()
    request.addfinalizer(reset)


@pytest.mark.uncollectif(lambda: current_version() < "5.4")
def test_delete_stack(setup_provider, provider, remove_test, set_grid_stack, request):
    """ Tests delete stack

    Metadata:
        test_flag: delete_object
    """
    stack_name = remove_test['stack']
    test_stack = stack.Stack(stack_name)
    test_stack.delete()
    test_stack.wait_for_delete()
    provider.refresh_provider_relationships()
    test_stack.wait_for_appear()
    request.addfinalizer(reset_grid_stack)
