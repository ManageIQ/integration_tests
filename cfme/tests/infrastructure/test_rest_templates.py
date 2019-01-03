# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.rest.gen_data import mark_vm_as_template
from cfme.rest.gen_data import vm as _vm
from cfme.utils.blockers import BZ
from cfme.utils.rest import (
    assert_response,
    delete_resources_from_collection,
    delete_resources_from_detail,
    query_resource_attributes,
)

pytestmark = [
    test_requirements.rest,
    pytest.mark.provider(classes=[InfraProvider], selector=ONE),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture(scope="function")
def vm(request, provider, appliance):
    return _vm(request, provider, appliance)


@pytest.fixture(scope="function")
def template(request, appliance, provider, vm):
    template = mark_vm_as_template(appliance, provider=provider, vm_name=vm)

    @request.addfinalizer
    def _finished():
        if template.id in appliance.rest_api.collections.templates:
            appliance.rest_api.collections.templates.action.delete(*template)

    return template


@pytest.mark.tier(3)
def test_query_template_attributes(request, appliance, provider, soft_assert):
    """Tests access to template attributes.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        initialEstimate: 1/4h
    """
    templates = appliance.rest_api.collections.templates.all
    if templates:
        template_rest = templates[0]
    else:
        vm_rest = vm(request, provider, appliance)
        template_rest = template(request, appliance, provider, vm_rest)

    outcome = query_resource_attributes(template_rest)
    for failure in outcome.failed:
        if failure.type == 'attribute' and failure.name == 'policy_events' and BZ(
                1546995, forced_streams=['5.8', '5.9', 'upstream']).blocks:
            continue
        soft_assert(False, '{0} "{1}": status: {2}, error: `{3}`'.format(
            failure.type, failure.name, failure.response.status_code, failure.error))


@pytest.mark.tier(3)
@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_set_ownership(appliance, template, from_detail):
    """Tests setting of template ownership.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: nansari
        initialEstimate: 1/8h
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
    assert_response(appliance)
    template.reload()
    assert hasattr(template, "evm_owner_id")
    assert template.evm_owner_id == user.id
    assert hasattr(template, "miq_group_id")
    assert template.miq_group_id == group.id


@pytest.mark.tier(2)
def test_delete_template_from_detail_post(template):
    """Tests deletion of template from detail using POST method.

    Testing BZ1422807

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        initialEstimate: 1/4h
    """
    delete_resources_from_detail([template], method='POST')


@pytest.mark.tier(2)
def test_delete_template_from_detail_delete(template):
    """Tests deletion of template from detail using DELETE method.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        initialEstimate: 1/4h
    """
    delete_resources_from_detail([template], method='DELETE')


@pytest.mark.tier(2)
def test_delete_template_from_collection(template):
    """Tests deletion of template from collection.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        initialEstimate: 1/4h
    """
    delete_resources_from_collection([template])
