# -*- coding: utf-8 -*-

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Region, flash, Quadicon, toolbar as tb
from utils import testgen
from utils.log import logger
from utils.wait import wait_for
import pytest


pytestmark = [pytest.mark.usefixtures("setup_cloud_providers")]

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


def test_delete_instance(provider_crud, remove_test):
    instance_name, image_name = map(remove_test.get, ('instance', 'image'))
    sel.force_navigate(
        'clouds_provider', context={'provider': provider_crud})
    sel.click(details_page.infoblock.element("Relationships", "Instances"))
    quad = Quadicon(instance_name, 'instance')
    if sel.is_displayed(quad):
        sel.check(quad.checkbox())
    tb.select("Configuration", "Remove selected items from the VMDB", invokes_alert=True)
    sel.handle_alert()
    flash.assert_message_match('Deletion initiated for 1 VM and Instance from the CFME Database')
    wait_for(lambda: not sel.is_displayed(quad), fail_condition=False,
             message="Wait instance to disappear", num_sec=1000, fail_func=sel.refresh)
    logger.info('Instance {} disappeared after deletion'.format(instance_name))
    provider_crud.refresh_provider_relationships()
    sel.click(details_page.infoblock.element("Relationships", "Instances"))
    wait_for(sel.is_displayed, func_args=[quad], fail_condition=False,
             message="Wait instance to reappear", num_sec=1000, fail_func=sel.refresh)
    logger.info('Instance {} reappeared after deletion'.format(instance_name))


def test_delete_image(provider_crud, remove_test):
    instance_name, image_name = map(remove_test.get, ('instance', 'image'))
    sel.force_navigate(
        'clouds_provider', context={'provider': provider_crud})
    sel.click(details_page.infoblock.element("Relationships", "Images"))
    tb.select('Grid View')
    quad = Quadicon(image_name, 'image')
    if sel.is_displayed(quad):
        sel.check(quad.checkbox())
    tb.select('Configuration', 'Remove selected items from the VMDB', invokes_alert=True)
    sel.handle_alert()
    flash.assert_message_contain(
        'Deletion initiated for 1 VM Template and Image from the CFME Database')
    wait_for(lambda: not sel.is_displayed(quad), fail_condition=False,
             message="Wait image to disappear", num_sec=1000, fail_func=sel.refresh)
    logger.info('Image  {} disappeared after deletion'.format(image_name))
    provider_crud.refresh_provider_relationships()
    sel.click(details_page.infoblock.element("Relationships", "Images"))
    tb.select('Grid View')
    wait_for(sel.is_displayed, func_args=[quad], fail_condition=False,
             message="Wait image to appear", num_sec=1000, fail_func=sel.refresh)
    logger.info('Image {} reappeared after deletion'.format(image_name))
