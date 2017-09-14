# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import mark_vm_as_template
from cfme.rest.gen_data import vm as _vm
from cfme.utils import error
from cfme.utils.version import current_version

pytestmark = [test_requirements.rest]


@pytest.fixture(scope="module")
def a_provider(request):
    return _a_provider(request)


@pytest.fixture(scope="function")
def vm(request, a_provider, appliance):
    return _vm(request, a_provider, appliance.rest_api)


@pytest.fixture(scope="function")
def template(request, appliance, a_provider, vm):
    template = mark_vm_as_template(appliance.rest_api, provider=a_provider, vm_name=vm)

    @request.addfinalizer
    def _finished():
        if template.id in appliance.rest_api.collections.templates:
            appliance.rest_api.collections.templates.action.delete(*template)

    return template


@pytest.mark.tier(3)
@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_set_ownership(appliance, template, from_detail):
    """Tests setting of template ownership.

    Metadata:
        test_flag: rest
    """
    if "set_ownership" not in appliance.rest_api.collections.templates.action.all:
        pytest.skip("set_ownership action for templates is not implemented in this version")
    group = appliance.rest_api.collections.groups.get(description='EvmGroup-super_administrator')
    user = appliance.rest_api.collections.users.get(userid='admin')
    data = {
        "owner": {"href": user.href},
        "group": {"href": group.href}
    }
    if from_detail:
        template.action.set_ownership(**data)
    else:
        data["href"] = template.href
        appliance.rest_api.collections.templates.action.set_ownership(**data)
    assert appliance.rest_api.response.status_code == 200
    template.reload()
    assert hasattr(template, "evm_owner_id")
    assert template.evm_owner_id == user.id
    assert hasattr(template, "miq_group_id")
    assert template.miq_group_id == group.id


@pytest.mark.tier(2)
# BZ1422807 that was fixed only in 5.8
@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_delete_template_from_detail_post(appliance, template):
    """Tests deletion of template from detail using POST method.

    Metadata:
        test_flag: rest
    """
    template.action.delete(force_method="post")
    assert appliance.rest_api.response.status_code == 200
    with error.expected("ActiveRecord::RecordNotFound"):
        template.action.delete(force_method="post")
    assert appliance.rest_api.response.status_code == 404


@pytest.mark.tier(2)
def test_delete_template_from_detail_delete(appliance, template):
    """Tests deletion of template from detail using DELETE method.

    Metadata:
        test_flag: rest
    """
    template.action.delete(force_method="delete")
    assert appliance.rest_api.response.status_code == 204
    with error.expected("ActiveRecord::RecordNotFound"):
        template.action.delete(force_method="delete")
    assert appliance.rest_api.response.status_code == 404


@pytest.mark.tier(2)
def test_delete_template_from_collection(appliance, template):
    """Tests deletion of template from collection.

    Metadata:
        test_flag: rest
    """
    appliance.rest_api.collections.templates.action.delete(template)
    assert appliance.rest_api.response.status_code == 200
    with error.expected("ActiveRecord::RecordNotFound"):
        appliance.rest_api.collections.templates.action.delete(template)
    assert appliance.rest_api.response.status_code == 404
