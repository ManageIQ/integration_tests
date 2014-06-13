# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621
import pytest

from cfme.automate.explorer import Namespace
from utils.randomness import generate_random_string
from utils.update import update
import utils.error as error
import cfme.tests.configure.test_access_control as tac

pytestmark = [pytest.mark.usefixtures("logged_in")]


def a_namespace():
    name = generate_random_string(8)
    description = generate_random_string(32)
    return Namespace(name=name, description=description)


def a_namespace_with_path():
    name = generate_random_string(8)
    n = Namespace.make_path('Factory', 'StateMachines', name)
    n.description = generate_random_string(32)
    return n


@pytest.fixture(params=[a_namespace, a_namespace_with_path])
def namespace(request):
    return request.param()


def test_namespace_crud(namespace):
    namespace.create()
    old_name = namespace.name
    with update(namespace):
        namespace.name = generate_random_string(8)
    with update(namespace):
        namespace.name = old_name
    namespace.delete()
    assert not namespace.exists()


def test_add_delete_namespace_nested(namespace):
    namespace.create()
    nested_ns = Namespace(name="Nested", parent=namespace)
    nested_ns.create()
    namespace.delete()
    assert not nested_ns.exists()


def test_duplicate_namespace_disallowed(namespace):
    namespace.create()
    with error.expected("Error during 'add': Validation failed: fqname must be unique"):
        namespace.create()


def test_permissions_namespace_crud():
    """ Tests that a namespace can be manipulated only with the right permissions"""
    tac.single_task_permission_test([['Automate', 'Explorer']],
                                    {'Namespace CRUD': lambda: test_namespace_crud(a_namespace())})
