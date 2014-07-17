import pytest
from cfme.automate.explorer import Class
from utils.randomness import generate_random_string
from utils.update import update
import utils.error as error
import cfme.tests.automate as ta


pytestmark = [pytest.mark.usefixtures("logged_in")]

make_namespace = pytest.fixture(scope='module')(ta.make_namespace)


@pytest.fixture
def a_class(make_namespace):
    return ta.a_class(make_namespace)


def test_class_crud(a_class):
    a_class.create()
    orig = a_class.description
    with update(a_class):
        a_class.description = 'edited'
    with update(a_class):
        a_class.description = orig
    a_class.delete()
    assert not a_class.exists()


def test_schema_crud(a_class):
    a_class.create()
    f1 = Class.SchemaField(name='foo')
    f2 = Class.SchemaField(name='bar')
    f3 = Class.SchemaField(name='baz')
    a_class.edit_schema(add_fields=(f1, f2))
    a_class.edit_schema(remove_fields=(f1,), add_fields=(f3,))


def test_add_class_inherited(a_class):
    subclass = Class(name=generate_random_string(8),
                     namespace=a_class.namespace,
                     description="subclass",
                     inherits_from=a_class)
    a_class.create()
    subclass.create()


def test_duplicate_class_disallowed(a_class):
    a_class.create()
    with error.expected("Name has already been taken"):
        a_class.create()


def test_same_class_name_different_namespace(make_namespace):
    other_namespace = ta.make_namespace()
    name = generate_random_string(8)
    cls1 = Class(name=name, namespace=make_namespace)
    cls2 = Class(name=name, namespace=other_namespace)
    cls1.create()
    cls2.create()
    # delete one and check the other still exists
    cls1.delete()
    assert cls2.exists()
