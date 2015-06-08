# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621
import fauxfactory
import pytest

from cfme.automate.explorer import Namespace, Domain
from utils.providers import setup_a_provider
from utils.update import update
from utils import version
import utils.error as error
import cfme.tests.configure.test_access_control as tac
import cfme.tests.automate as ta

pytestmark = [pytest.mark.usefixtures("logged_in")]


@pytest.fixture(scope="module")
def domain(request):
    domain = Domain(name=fauxfactory.gen_alphanumeric(), enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture(
    scope="function",
    params=[ta.a_namespace, ta.a_namespace_with_path])
def namespace(request, domain):
    # don't test with existing paths on upstream (there aren't any)
    if request.param is ta.a_namespace_with_path and version.current_version() == version.LATEST:
        pytest.skip("don't test with existing paths on upstream (there aren't any)")
    return request.param(domain=domain)


@pytest.fixture
def setup_single_provider():
    setup_a_provider()


def test_namespace_crud(namespace):
    namespace.create()
    old_name = namespace.name
    with update(namespace):
        namespace.name = fauxfactory.gen_alphanumeric(8)
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


@pytest.mark.meta(blockers=[1136518])
def test_duplicate_namespace_disallowed(namespace):
    namespace.create()
    with error.expected("Name has already been taken"):
        namespace.create()


# provider needed as workaround for bz1035399
@pytest.mark.meta(blockers=[1140331])
def test_permissions_namespace_crud(setup_single_provider, domain):
    """ Tests that a namespace can be manipulated only with the right permissions"""
    tac.single_task_permission_test([['Automate', 'Explorer']],
                                    {'Namespace CRUD':
                                     lambda: test_namespace_crud(ta.a_namespace(domain=domain))})
