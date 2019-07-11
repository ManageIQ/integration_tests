# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.klass import ClassSchemaEditView
from cfme.utils.update import update

pytestmark = [test_requirements.automate]


@pytest.fixture(
    scope="function",
    params=["plain", "nested_existing"])
def get_namespace(request, domain):
    namespace = domain.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )
    if request.param == 'plain':
        yield namespace
    else:
        namespace = namespace.namespaces.create(
            name=fauxfactory.gen_alpha(),
            description=fauxfactory.gen_alpha()
        )
        yield namespace
    namespace.delete_if_exists()


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_class_crud(get_namespace):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: critical
        initialEstimate: 1/30h
        tags: automate
    """
    a_class = get_namespace.classes.create(
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


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_schema_crud(get_namespace):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: critical
        initialEstimate: 1/20h
        tags: automate
    """
    a_class = get_namespace.classes.create(
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
def test_schema_duplicate_field_disallowed(klass):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/16h
        tags: automate
    """
    field = fauxfactory.gen_alpha()
    klass.schema.add_field(name=field, type='Relationship')
    with pytest.raises(Exception, match='Name has already been taken'):
        klass.schema.add_field(name=field, type='Relationship')


@pytest.mark.tier(2)
def test_duplicate_class_disallowed(get_namespace):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseposneg: negative
        initialEstimate: 1/30h
        tags: automate
    """
    name = fauxfactory.gen_alphanumeric()
    get_namespace.classes.create(name=name)
    with pytest.raises(Exception, match="Name has already been taken"):
        get_namespace.classes.create(name=name)


@pytest.mark.tier(2)
def test_same_class_name_different_namespace(domain):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        initialEstimate: 1/16h
        tags: automate
    """
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


@pytest.mark.tier(3)
@pytest.mark.polarion('RHCF3-3455')
def test_class_display_name_unset_from_ui(get_namespace):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        initialEstimate: 1/30h
        tags: automate
    """
    a_class = get_namespace.classes.create(
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


@pytest.mark.tier(3)
def test_automate_schema_field_without_type(klass):
    """It shouldn't be possible to add a field without specifying a type.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
        tags: automate
        testSteps:
            1. Create a schema field that does not specify a type
            2. Save the schema
        expectedResults:
            1.
            2. it is not possible to add a field that does not specify the type
               (assertion, attribute, relationship, ...)

    Bugzilla:
        1365442
    """
    schema_field = fauxfactory.gen_alphanumeric()
    with pytest.raises(AssertionError):
        klass.schema.add_fields({'name': schema_field, 'data_type': 'String'})
    view = klass.create_view(ClassSchemaEditView)
    assert view.schema.save_button.disabled
    assert view.schema.reset_button.disabled
    assert not view.schema.cancel_button.disabled
