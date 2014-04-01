# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621
import pytest

from cfme.automate.explorer import Namespace
from utils.randomness import generate_random_string
from utils.update import update
import utils.error as error

pytestmark = [pytest.mark.usefixtures("logged_in")]


@pytest.fixture
def gen_namespace():
    name = generate_random_string(8)
    description = generate_random_string(32)
    return Namespace(name=name, description=description)


@pytest.fixture
def gen_namespace_path():
    name = generate_random_string(8)
    description = generate_random_string(32)
    path = ('Factory', 'StateMachines')
    return Namespace(name=name, description=description, path=path)


def test_add(gen_namespace):
    gen_namespace.create()


def test_add_nested(gen_namespace):
    gen_namespace.create()
    nested_ns = Namespace(name="Nested", path=gen_namespace.path)
    nested_ns.create()


def test_delete_nested(gen_namespace):
    gen_namespace.create()
    nested_ns = Namespace(name="Nested", path=gen_namespace.path)
    nested_ns.create()
    gen_namespace.delete()
    assert not gen_namespace.exists()


def test_edit(gen_namespace):
    gen_namespace.create()
    old_name = gen_namespace.name
    with update(gen_namespace) as gen_namespace:
        gen_namespace.name = generate_random_string(8)
    with update(gen_namespace) as gen_namespace:
        gen_namespace.name = old_name


def test_delete(gen_namespace):
    gen_namespace.create()
    gen_namespace.delete(cancel=False)


def test_add_with_path(gen_namespace_path):
    gen_namespace_path.create()


def test_edit_with_path(gen_namespace_path):
    gen_namespace_path.create()
    old_name = gen_namespace_path.name
    with update(gen_namespace_path) as gen_namespace_path:
        gen_namespace_path.name = generate_random_string(8)
    with update(gen_namespace_path) as gen_namespace_path:
        gen_namespace_path.name = old_name


def test_delete_with_path(gen_namespace_path):
    gen_namespace_path.create()
    gen_namespace_path.delete(cancel=False)


def test_duplicate_disallowed(gen_namespace):
    gen_namespace.create()
    with error.expected("Error during 'add': Validation failed: fqname must be unique"):
        gen_namespace.create()

    
