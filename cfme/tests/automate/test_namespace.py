# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621
import pytest

import cfme.web_ui.flash as flash
from cfme.automate.explorer import Namespace
import utils.error as error
from utils.randomness import generate_random_string
from utils.update import update


@pytest.fixture(scope='module')
def gen_namespace():
    name = generate_random_string(8)
    description = generate_random_string(32)
    return Namespace(name=name, description=description)


@pytest.fixture(scope='module')
def gen_namespace_path():
    name = generate_random_string(8)
    description = generate_random_string(32)
    path = ('Factory', 'StateMachines')
    return Namespace(name=name, description=description, path=path)


def test_namespace_add(gen_namespace):
    gen_namespace.create()
    flash.assert_message_match('Automate Namespace "%s" was added' % gen_namespace.name)


def test_namespace_edit(gen_namespace):
    old_name = gen_namespace.name
    with update(gen_namespace) as gen_namespace:
        gen_namespace.name = generate_random_string(8)
    flash.assert_message_match('Automate Namespace "%s" was saved' % gen_namespace.name)
    with update(gen_namespace) as gen_namespace:
        gen_namespace.name = old_name
    flash.assert_message_match('Automate Namespace "%s" was saved' % gen_namespace.name)


def test_namespace_delete(gen_namespace):
    gen_namespace.delete(cancel=False)
    flash.assert_message_match('Automate Namespace "%s": Delete successful'
                               % gen_namespace.description)
    flash.assert_message_match('The selected Automate Namespaces were deleted')


def test_namespace_add_with_path(gen_namespace_path):
    gen_namespace_path.create()
    flash.assert_message_match('Automate Namespace "%s" was added' % gen_namespace_path.name)


def test_namespace_edit_with_path(gen_namespace_path):
    old_name = gen_namespace_path.name
    with update(gen_namespace_path) as gen_namespace_path:
        gen_namespace_path.name = generate_random_string(8)
    flash.assert_message_match('Automate Namespace "%s" was saved' % gen_namespace_path.name)
    with update(gen_namespace_path) as gen_namespace_path:
        gen_namespace_path.name = old_name
    flash.assert_message_match('Automate Namespace "%s" was saved' % gen_namespace_path.name)


def test_namespace_delete_with_path(gen_namespace_path):
    gen_namespace_path.delete(cancel=False)
    flash.assert_message_match('Automate Namespace "%s": Delete successful'
                               % gen_namespace_path.description)
    flash.assert_message_match('The selected Automate Namespaces were deleted')
