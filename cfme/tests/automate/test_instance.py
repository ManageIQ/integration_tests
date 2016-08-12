# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import fauxfactory
import pytest
from utils.update import update
import utils.error as error
import cfme.tests.automate as ta


@pytest.fixture(scope='module')
def make_class(request):
    return ta.make_class(request=request)


@pytest.fixture(scope="function")
def an_instance(request, make_class):
    return ta.an_instance(make_class, request=request)


@pytest.mark.tier(2)
def test_instance_crud(an_instance):
    an_instance.create()
    origname = an_instance.name
    with update(an_instance):
        an_instance.name = fauxfactory.gen_alphanumeric(8)
        an_instance.description = "updated"
    with update(an_instance):
        an_instance.name = origname
    an_instance.delete()
    assert not an_instance.exists()


@pytest.mark.tier(2)
def test_duplicate_disallowed(an_instance):
    an_instance.create()
    with error.expected("Name has already been taken"):
        an_instance.create(allow_duplicate=True)


@pytest.mark.meta(blockers=[1148541])
@pytest.mark.tier(3)
def test_display_name_unset_from_ui(request, an_instance):
    an_instance.create()
    request.addfinalizer(an_instance.delete)
    with update(an_instance):
        an_instance.display_name = fauxfactory.gen_alphanumeric()
    assert an_instance.exists
    with update(an_instance):
        an_instance.display_name = ""
    assert an_instance.exists
