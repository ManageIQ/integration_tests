# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import fauxfactory
import pytest
from cfme.automate.explorer import Namespace, Class, Method, Domain
from utils.update import update
import utils.error as error


def _make_namespace(domain):
    name = fauxfactory.gen_alphanumeric(8)
    description = fauxfactory.gen_alphanumeric(32)
    ns = Namespace(name=name, description=description, parent=domain)
    ns.create()
    return ns


def _make_class(domain):
    name = fauxfactory.gen_alphanumeric(8)
    description = fauxfactory.gen_alphanumeric(32)
    cls = Class(name=name, description=description, namespace=_make_namespace(domain))
    cls.create()
    return cls


@pytest.fixture(scope="module")
def domain(request):
    domain = Domain(name=fauxfactory.gen_alphanumeric(), enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture(scope='module')
def a_class(domain):
    return _make_class(domain)


@pytest.fixture
def a_method(a_class):
    return Method(name=fauxfactory.gen_alphanumeric(8),
                  data="foo.bar()",
                  cls=a_class)


@pytest.mark.tier(2)
def test_method_crud(a_method):
    a_method.create()
    origname = a_method.name
    with update(a_method):
        a_method.name = fauxfactory.gen_alphanumeric(8)
        a_method.data = "bar"
    with update(a_method):
        a_method.name = origname
    a_method.delete()
    assert not a_method.exists()


@pytest.mark.tier(2)
def test_duplicate_method_disallowed(a_method):
    a_method.create()
    with error.expected("Name has already been taken"):
        a_method.create(allow_duplicate=True)
