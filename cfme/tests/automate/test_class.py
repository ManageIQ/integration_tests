import pytest
from cfme.automate.explorer import Namespace, Class
from utils.randomness import generate_random_string
from utils.update import update
import utils.error as error


pytestmark = [pytest.mark.usefixtures("logged_in")]


def _make_namespace():
    name = generate_random_string(8)
    description = generate_random_string(32)
    ns = Namespace(name=name, description=description)
    ns.create()
    return ns


@pytest.fixture(scope='module')
def a_namespace():
    return _make_namespace()


@pytest.fixture
def a_class(a_namespace):
    return Class(name=generate_random_string(8),
                 description=generate_random_string(32),
                 namespace=a_namespace)


def test_crud(a_class):
    a_class.create()
    orig = a_class.description
    with update(a_class):
        a_class.description = 'edited'
    with update(a_class):
        a_class.description = orig
    a_class.delete()
    assert not a_class.exists()


def test_add_inherited(a_class):
    subclass = Class(name=generate_random_string(8),
                     namespace=a_class.namespace,
                     description="subclass",
                     inherits_from=a_class)
    a_class.create()
    subclass.create()


def test_duplicate_disallowed(a_class):
    a_class.create()
    with error.expected("Name has already been taken"):
        a_class.create()


def test_same_name_different_namespace(a_namespace):
    other_namespace = _make_namespace()
    name = generate_random_string(8)
    cls1 = Class(name=name, namespace=a_namespace)
    cls2 = Class(name=name, namespace=other_namespace)
    cls1.create()
    cls2.create()
    # delete one and check the other still exists
    cls1.delete()
    assert cls2.exists()
