import pytest
from cfme.automate.explorer import Namespace, Class, Instance
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
def an_instance(a_class):
    return Instance(name=generate_random_string(8),
                    description=generate_random_string(32),
                    cls=a_class)


def test_instance_crud(an_instance):
    an_instance.create()
    origname = an_instance.name
    with update(an_instance):
        an_instance.name = generate_random_string(8)
        an_instance.description = "updated"
    with update(an_instance):
        an_instance.name = origname
    an_instance.delete()
    assert not an_instance.exists()


def test_duplicate_disallowed(an_instance):
    an_instance.create()
    with error.expected("Name has already been taken"):
        an_instance.create()
