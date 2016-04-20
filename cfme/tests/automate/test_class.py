# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from cfme.automate.explorer import Class
from utils.update import update
import utils.error as error
import cfme.tests.automate as ta


pytestmark = [pytest.mark.usefixtures("logged_in")]


@pytest.fixture(scope="module")
def make_namespace(request):
    return ta.make_namespace(request=request)


@pytest.fixture(scope="function")
def a_class(make_namespace):
    return ta.a_class(make_namespace)


@pytest.mark.tier(2)
def test_class_crud(a_class):
    a_class.create()
    orig = a_class.description
    with update(a_class):
        a_class.description = 'edited'
    with update(a_class):
        a_class.description = orig
    a_class.delete()
    assert not a_class.exists()


@pytest.mark.tier(2)
def test_schema_crud(a_class):
    a_class.create()
    f1 = Class.SchemaField(name='foo')
    f2 = Class.SchemaField(name='bar')
    f3 = Class.SchemaField(name='baz')
    a_class.edit_schema(add_fields=(f1, f2))
    a_class.edit_schema(remove_fields=(f1,), add_fields=(f3,))


# The inheritance box has been removed from the UI until it is implemented properly,
# see 1138859
#
# def test_add_class_inherited(a_class):
#     subclass = Class(name=fauxfactory.gen_alphanumeric(8),
#                      namespace=a_class.namespace,
#                      description="subclass",
#                      inherits_from=a_class)
#     a_class.create()
#     subclass.create()


@pytest.mark.tier(2)
def test_duplicate_class_disallowed(a_class):
    a_class.create()
    with error.expected("Name has already been taken"):
        a_class.create(allow_duplicate=True)


@pytest.mark.tier(2)
def test_same_class_name_different_namespace(make_namespace):
    other_namespace = ta.make_namespace()
    name = fauxfactory.gen_alphanumeric(8)
    cls1 = Class(name=name, namespace=make_namespace)
    cls2 = Class(name=name, namespace=other_namespace)
    cls1.create()
    cls2.create()
    # delete one and check the other still exists
    cls1.delete()
    assert cls2.exists()


@pytest.mark.meta(blockers=[1148541])
@pytest.mark.tier(3)
def test_display_name_unset_from_ui(request, a_class):
    a_class.create()
    request.addfinalizer(a_class.delete)
    with update(a_class):
        a_class.display_name = fauxfactory.gen_alphanumeric()
    assert a_class.exists
    with update(a_class):
        a_class.display_name = ""
    assert a_class.exists
