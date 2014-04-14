import pytest
from cfme.automate.explorer import Namespace, Class, Method
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


def _make_class():
    name = generate_random_string(8)
    description = generate_random_string(32)
    cls = Class(name=name, description=description, namespace=_make_namespace())
    cls.create()
    return cls


@pytest.fixture(scope='module')
def a_class():
    return _make_class()


@pytest.fixture
def a_method(a_class):
    return Method(name=generate_random_string(8),
                  data="foo.bar()",
                  cls=a_class)


def test_method_crud(a_method):
    a_method.create()
    origname = a_method.name
    with update(a_method):
        a_method.name = generate_random_string(8)
        a_method.data = "bar"
    with update(a_method):
        a_method.name = origname
    a_method.delete()
    assert not a_method.exists()


def test_duplicate_method_disallowed(a_method):
    a_method.create()
    with error.expected("Name has already been taken"):
        a_method.create()
