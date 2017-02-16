# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import mark_vm_as_template
from cfme.rest.gen_data import vm as _vm
from utils import error
from utils.blockers import BZ

pytestmark = [pytest.mark.ignore_stream("5.4"), test_requirements.rest]


@pytest.fixture(scope="module")
def a_provider():
    return _a_provider()


@pytest.fixture(scope="function")
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
    """Tests setting of template ownership.

    Metadata:
        test_flag: rest
    """
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
    assert rest_api.response.status_code == 200
    template.reload()
    assert hasattr(template, "evm_owner_id")
    assert template.evm_owner_id == user.id
    assert hasattr(template, "miq_group_id")
    assert template.miq_group_id == group.id


@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[BZ(1422807, forced_streams=["5.7", "upstream"])])
def test_delete_template_from_detail_post(rest_api, template):
    """Tests deletion of template from detail using POST method.

    Metadata:
        test_flag: rest
    """
    template.action.delete(force_method="post")
    assert rest_api.response.status_code == 200
    with error.expected("ActiveRecord::RecordNotFound"):
        template.action.delete(force_method="post")
    assert rest_api.response.status_code == 404


@pytest.mark.tier(2)
def test_delete_template_from_detail_delete(rest_api, template):
    """Tests deletion of template from detail using DELETE method.

    Metadata:
        test_flag: rest
    """
    template.action.delete(force_method="delete")
    assert rest_api.response.status_code == 204
    with error.expected("ActiveRecord::RecordNotFound"):
        template.action.delete(force_method="delete")
    assert rest_api.response.status_code == 404


@pytest.mark.tier(2)
def test_delete_template_from_collection(rest_api, template):
    """Tests deletion of template from collection.

    Metadata:
        test_flag: rest
    """
    rest_api.collections.templates.action.delete(template)
    assert rest_api.response.status_code == 200
    with error.expected("ActiveRecord::RecordNotFound"):
        rest_api.collections.templates.action.delete(template)
    assert rest_api.response.status_code == 404
