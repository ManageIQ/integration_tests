
# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621
import pytest

from cfme.automate.explorer import Namespace
from utils.randomness import generate_random_string
from utils.update import update
from utils import version
import utils.error as error
import cfme.tests.configure.test_access_control as tac
import cfme.tests.automate as ta

pytestmark = [pytest.mark.usefixtures("logged_in")]


@pytest.fixture(
    scope="function",
    params=[ta.a_namespace, ta.a_namespace_with_path])
def namespace(request):
    # don't test with existing paths on upstream (there aren't any)
    if request.param is ta.a_namespace_with_path and version.current_version() >= "5.3":
        pytest.skip("don't test with existing paths on upstream (there aren't any)")
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


@pytest.mark.bugzilla(1136518)
def test_duplicate_namespace_disallowed(namespace):
    namespace.create()
    with error.expected("Name has already been taken"):
        namespace.create()


# provider needed as workaround for bz1035399
@pytest.mark.bugzilla(1140331)
def test_permissions_namespace_crud(setup_cloud_providers):
    """ Tests that a namespace can be manipulated only with the right permissions"""
    tac.single_task_permission_test([['Automate', 'Explorer']],
                                    {'Namespace CRUD':
                                     lambda: test_namespace_crud(ta.a_namespace())})
