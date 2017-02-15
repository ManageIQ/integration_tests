# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from utils import error
from utils.update import update


pytestmark = [test_requirements.automate]


@pytest.yield_fixture(scope='module')
def domain():
    dc = DomainCollection()
    d = dc.create(
        name='test_{}'.format(fauxfactory.gen_alpha()),
        description='desc_{}'.format(fauxfactory.gen_alpha()),
        enabled=True)
    yield d
    d.delete()


@pytest.fixture(
    scope="function",
    params=["plain", "nested_existing"])
def namespace(request, domain):
    ns = domain.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )
    if request.param == 'plain':
        return ns
    else:
        return ns.namespaces.create(
            name=fauxfactory.gen_alpha(),
            description=fauxfactory.gen_alpha()
        )


@pytest.mark.tier(2)
def test_class_crud(namespace):
    a_class = namespace.classes.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric()
    )
    orig = a_class.description
    with update(a_class):
        a_class.description = 'edited'
    with update(a_class):
        a_class.description = orig
    a_class.delete()
    assert not a_class.exists


@pytest.mark.tier(2)
def test_schema_crud(request, namespace):
    a_class = namespace.classes.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric()
    )
    request.addfinalizer(a_class.delete_if_exists)
    f1 = fauxfactory.gen_alpha()
    f2 = fauxfactory.gen_alpha()
    f3 = fauxfactory.gen_alpha()
    a_class.schema.add_fields(
        {'name': f1, 'type': 'Relationship'},
        {'name': f2, 'type': 'Attribute'},)
    a_class.schema.add_field(name=f3, type='Relationship')
    a_class.schema.delete_field(f1)
    assert set(a_class.schema.schema_field_names) == {f2, f3}
    # TODO: Combined add/remove/update test


@pytest.mark.tier(2)
def test_duplicate_class_disallowed(namespace):
    name = fauxfactory.gen_alphanumeric()
    namespace.classes.create(name=name)
    with error.expected("Name has already been taken"):
        namespace.classes.create(name=name)


@pytest.mark.tier(2)
def test_same_class_name_different_namespace(request, domain):
    ns1 = domain.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )
    request.addfinalizer(ns1.delete_if_exists)
    ns2 = domain.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )
    request.addfinalizer(ns2.delete_if_exists)

    c1 = ns1.classes.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric()
    )
    c2 = ns2.classes.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric()
    )
    assert c1.exists
    assert c2.exists

    c1.delete()
    assert not c1.exists
    assert c2.exists


@pytest.mark.meta(blockers=[1148541])
@pytest.mark.tier(3)
def test_display_name_unset_from_ui(request, namespace):
    a_class = namespace.classes.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric()
    )
    request.addfinalizer(a_class.delete_if_exists)
    with update(a_class):
        a_class.display_name = fauxfactory.gen_alphanumeric()
    assert a_class.exists
    with update(a_class):
        a_class.display_name = ""
    assert a_class.exists
