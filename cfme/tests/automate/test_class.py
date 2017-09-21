# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.utils import error
from cfme.utils.blockers import BZ
from cfme.utils.update import update


pytestmark = [test_requirements.automate]


@pytest.yield_fixture(scope='module')
def domain(appliance):
    dc = DomainCollection(appliance)
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
@pytest.mark.meta(blockers=[1404788])
def test_schema_crud(request, namespace):
    a_class = namespace.classes.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric()
    )
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
@pytest.mark.meta(blockers=[1404788])
def test_schema_duplicate_field_disallowed(request, domain):
    ns = domain.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )
    a_class = ns.classes.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric()
    )
    field = fauxfactory.gen_alpha()
    a_class.schema.add_field(name=field, type='Relationship')
    with error.expected('Name has already been taken'):
        a_class.schema.add_field(name=field, type='Relationship')


@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[BZ(1428424, forced_streams=['5.8', 'upstream'])])
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
    ns2 = domain.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )

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
@pytest.mark.polarion('RHCF3-3455')
def test_class_display_name_unset_from_ui(request, namespace):
    a_class = namespace.classes.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric()
    )
    with update(a_class):
        a_class.display_name = fauxfactory.gen_alphanumeric()
    assert a_class.exists
    with update(a_class):
        a_class.display_name = ""
    assert a_class.exists
