# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.automate.explorer.domain import DomainCollection

from cfme.utils import error
from cfme.utils.update import update


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
    scope="module",
    params=["plain", "nested_existing"])
def parent_namespace(request, domain):
    if request.param == 'plain':
        return domain
    else:
        return domain.namespaces.create(
            name=fauxfactory.gen_alpha(),
            description=fauxfactory.gen_alpha()
        )


@pytest.mark.tier(1)
def test_namespace_crud(request, parent_namespace):
    ns = parent_namespace.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha())
    assert ns.exists
    updated_description = "editdescription{}".format(fauxfactory.gen_alpha())
    with update(ns):
        ns.description = updated_description
    assert ns.exists
    ns.delete(cancel=True)
    assert ns.exists
    ns.delete()
    assert not ns.exists


@pytest.mark.tier(1)
def test_namespace_delete_from_table(request, parent_namespace):
    generated = []
    for _ in range(3):
        namespace = parent_namespace.namespaces.create(
            name=fauxfactory.gen_alpha(),
            description=fauxfactory.gen_alpha())
        generated.append(namespace)

    parent_namespace.namespaces.delete(*generated)
    for namespace in generated:
        assert not namespace.exists


@pytest.mark.tier(2)
def test_duplicate_namespace_disallowed(request, parent_namespace):
    ns = parent_namespace.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha())
    with error.expected("Name has already been taken"):
        parent_namespace.namespaces.create(
            name=ns.name,
            description=ns.description)
