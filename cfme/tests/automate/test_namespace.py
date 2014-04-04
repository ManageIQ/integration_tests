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
def a_namespace():
    name = generate_random_string(8)
    description = generate_random_string(32)
    return Namespace(name=name, description=description)


@pytest.fixture
def a_namespace_with_path():
    name = generate_random_string(8)
    description = generate_random_string(32)
    path = ('Factory', 'StateMachines')
    return Namespace(name=name, description=description, path=path)


def test_add(a_namespace):
    a_namespace.create()


def test_add_nested(a_namespace):
    a_namespace.create()
    nested_ns = Namespace(name="Nested", path=a_namespace.path)
    nested_ns.create()


def test_delete_nested(a_namespace):
    a_namespace.create()
    nested_ns = Namespace(name="Nested", path=a_namespace.path)
    nested_ns.create()
    a_namespace.delete()
    assert not a_namespace.exists()


def test_edit(a_namespace):
    a_namespace.create()
    old_name = a_namespace.name
    with update(a_namespace):
        a_namespace.name = generate_random_string(8)
    with update(a_namespace):
        a_namespace.name = old_name


def test_delete(a_namespace):
    a_namespace.create()
    a_namespace.delete()


def test_add_with_path(a_namespace_with_path):
    a_namespace_with_path.create()


def test_edit_with_path(a_namespace_with_path):
    a_namespace_with_path.create()
    old_name = a_namespace_with_path.name
    with update(a_namespace_with_path):
        a_namespace_with_path.name = generate_random_string(8)
    with update(a_namespace_with_path):
        a_namespace_with_path.name = old_name


def test_delete_with_path(a_namespace_with_path):
    a_namespace_with_path.create()
    a_namespace_with_path.delete(cancel=False)


def test_duplicate_disallowed(a_namespace):
    a_namespace.create()
    with error.expected("Error during 'add': Validation failed: fqname must be unique"):
        a_namespace.create()

    
