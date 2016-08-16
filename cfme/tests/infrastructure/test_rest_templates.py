# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pytest

from cfme.rest import a_provider as _a_provider
from cfme.rest import mark_vm_as_template
from cfme.rest import vm as _vm
from utils import error

pytestmark = [pytest.mark.ignore_stream("5.4")]


@pytest.fixture(scope="module")
def a_provider():
    return _a_provider()


@pytest.fixture(scope="module")
def vm(request, a_provider, rest_api_modscope):
    return _vm(request, a_provider, rest_api_modscope)


@pytest.fixture(scope="function")
def template(request, rest_api, a_provider, vm):
    template = mark_vm_as_template(rest_api, provider=a_provider, vm_name=vm)

    @request.addfinalizer
    def _finished():
        if template.id in rest_api.collections.templates:
            rest_api.collections.templates.action.delete(*template)

    return template


@pytest.mark.tier(3)
@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_set_ownership(rest_api, template, from_detail):
    if "set_ownership" not in rest_api.collections.templates.action.all:
        pytest.skip("set_ownership action for templates is not implemented in this version")
    group = rest_api.collections.groups.get(description='EvmGroup-super_administrator')
    user = rest_api.collections.users.get(userid='admin')
    data = {
        "owner": {"href": user.href},
        "group": {"href": group.href}
    }
    if from_detail:
        template.action.set_ownership(**data)
    else:
        data["href"] = template.href
        rest_api.collections.templates.action.set_ownership(**data)
    template.reload()
    assert hasattr(template, "evm_owner_id")
    assert template.evm_owner_id == user.id
    assert hasattr(template, "miq_group_id")
    assert template.miq_group_id == group.id


@pytest.mark.tier(2)
@pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
def test_delete_template(rest_api, template, multiple):
    if multiple:
        rest_api.collections.templates.action.delete(template)
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.templates.action.delete(template)
    else:
        template.action.delete()
        with error.expected("ActiveRecord::RecordNotFound"):
            template.action.delete()
