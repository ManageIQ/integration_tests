# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider.azure import AzureProvider
from cfme.utils.generators import random_vm_name


pytestmark = [
    test_requirements.quota,
    pytest.mark.long_running,
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([AzureProvider], scope='function',
                         required_fields=[["provisioning", "image"]])]


@pytest.fixture
def prov_data(appliance, provisioning):
    """Keeping it as a fixture because we need to call 'provisioning' from this fixture as well as
       using this same fixture in various tests.
    """
    instance_type = "d2s_v3" if appliance.version < "5.10" else "d2s_v3".capitalize()
    return {
        "catalog": {"vm_name": random_vm_name(context="quota")},
        "environment": {"automatic_placement": True},
        "properties": {"instance_type": partial_match(instance_type)},
        "customize": {
            "admin_username": provisioning["customize_username"],
            "root_password": provisioning["customize_password"],
        },
    }


@pytest.fixture
def set_child_tenant_quota(request, appliance, new_child):
    """This fixture assigns quota to child tenant"""
    field, value = request.param
    new_child.set_quota(**{"{}_cb".format(field): True, field: value})
    yield
    appliance.server.login_admin()
    new_child.set_quota(**{"{}_cb".format(field): False})


@pytest.fixture
def set_project_quota(request, appliance, new_project):
    """This fixture assigns quota to project"""
    field, value = request.param
    new_project.set_quota(**{"{}_cb".format(field): True, field: value})
    yield
    appliance.server.login_admin()
    new_project.set_quota(**{"{}_cb".format(field): False})


@pytest.fixture(scope="module")
def new_tenant(appliance):
    """This fixture creates new tenant under root tenant(My Company)"""
    collection = appliance.collections.tenants
    tenant = collection.create(
        name="tenant_{}".format(fauxfactory.gen_alphanumeric()),
        description="tenant_des{}".format(fauxfactory.gen_alphanumeric()),
        parent=collection.get_root_tenant(),
    )
    yield tenant
    if tenant.exists:
        tenant.delete()


@pytest.fixture(scope="module")
def new_child(appliance, new_tenant):
    """The fixture creates new child tenant"""
    child_tenant = appliance.collections.tenants.create(
        name="tenant_{}".format(fauxfactory.gen_alphanumeric()),
        description="tenant_des{}".format(fauxfactory.gen_alphanumeric()),
        parent=new_tenant,
    )
    yield child_tenant
    if child_tenant.exists:
        child_tenant.delete()


@pytest.fixture(scope="module")
def new_group_child(appliance, new_child, new_tenant):
    """This fixture creates new group assigned by new child tenant"""
    group = appliance.collections.groups.create(
        description="group_{}".format(fauxfactory.gen_alphanumeric()),
        role="EvmRole-super_administrator",
        tenant="My Company/{parent}/{child}".format(parent=new_tenant.name, child=new_child.name),
    )
    yield group
    if group.exists:
        group.delete()


@pytest.fixture(scope="module")
def new_user_child(appliance, new_group_child):
    """This fixture creates new user which assigned to new child tenant"""
    user = appliance.collections.users.create(
        name="user_{}".format(fauxfactory.gen_alphanumeric().lower()),
        credential=Credential(principal='uid{}'.format(fauxfactory.gen_alphanumeric(4)),
                              secret='{password}'.format(password=fauxfactory.gen_alphanumeric(4))),
        email=fauxfactory.gen_email(),
        groups=new_group_child,
        cost_center="Workload",
        value_assign="Database",
    )
    yield user
    if user.exists:
        user.delete()


@pytest.fixture(scope="module")
def new_project(appliance):
    """This fixture creates new project"""
    collection = appliance.collections.projects
    project = collection.create(
        name="project_{}".format(fauxfactory.gen_alphanumeric()),
        description="project_des{}".format(fauxfactory.gen_alphanumeric()),
        parent=collection.get_root_tenant(),
    )
    yield project
    if project.exists:
        project.delete()


@pytest.fixture(scope="module")
def new_group_project(appliance, new_project):
    """This fixture creates new group and assigned by new project"""
    group = appliance.collections.groups.create(
        description="group_{}".format(fauxfactory.gen_alphanumeric()),
        role="EvmRole-super_administrator",
        tenant="My Company/{project}".format(project=new_project.name),
    )
    yield group
    if group.exists:
        group.delete()


@pytest.fixture(scope="module")
def new_user_project(appliance, new_group_project):
    """This fixture creates new user which is assigned to new group and project"""
    user = appliance.collections.users.create(
        name="user_{}".format(fauxfactory.gen_alphanumeric().lower()),
        credential=Credential(principal='uid{}'.format(fauxfactory.gen_alphanumeric(4)),
                              secret='{password}'.format(password=fauxfactory.gen_alphanumeric(4))),
        email=fauxfactory.gen_email(),
        groups=new_group_project,
        cost_center="Workload",
        value_assign="Database",
    )
    yield user
    if user.exists:
        user.delete()


# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize(
    ["set_child_tenant_quota", "custom_prov_data", "extra_msg", "approve"],
    [
        [("cpu", 1), {}, "", False],
        [("storage", 0.001), {}, "", False],
        [("memory", 2), {}, "", False],
        [("vm", 1), {"catalog": {"num_vms": "4"}}, "###", True],
    ],
    indirect=["set_child_tenant_quota"],
    ids=["max_cpu", "max_storage", "max_memory", "max_vms"],
)
def test_child_tenant_quota_enforce_via_lifecycle_cloud(
    request,
    appliance,
    provider,
    new_user_child,
    set_child_tenant_quota,
    extra_msg,
    approve,
    custom_prov_data,
    prov_data,
    provisioning,
):
    """Test Child Quota in UI

    Polarion:
        assignee: ghubale
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/8h
        tags: quota
        testSteps:
            1. Create a child tenant
            2. Assign quota to child tenant
            3. Provision instance over the assigned child's quota
            4. Check whether quota is exceeded or not
    """
    with new_user_child:
        recursive_update(prov_data, custom_prov_data)
        recursive_update(
            prov_data,
            {
                "request": {
                    "email": fauxfactory.gen_email(),
                    "first_name": fauxfactory.gen_alphanumeric(),
                    "last_name": fauxfactory.gen_alphanumeric(),
                    "manager_name": "{name}".format(name=fauxfactory.gen_alphanumeric()),
                }
            },
        )
        prov_data.update({"template_name": provisioning["image"]["name"]})
        request_description = "Provision from [{template}] to [{vm}{msg}]".format(
            template=provisioning["image"]["name"], vm=prov_data['catalog']['vm_name'],
            msg=extra_msg)
        appliance.collections.cloud_instances.create(
            prov_data['catalog']['vm_name'],
            provider,
            prov_data,
            auto_approve=approve,
            override=True,
            request_description=request_description,
        )
        provision_request = appliance.collections.requests.instantiate(request_description)
        provision_request.wait_for_request(method="ui")
        request.addfinalizer(provision_request.remove_request)
        assert provision_request.row.reason.text == "Quota Exceeded"


# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize(
    ["set_project_quota", "custom_prov_data", "extra_msg", "approve"],
    [
        [("cpu", 1), {}, "", False],
        [("storage", 0.001), {}, "", False],
        [("memory", 2), {}, "", False],
        [("vm", 1), {"catalog": {"num_vms": "4"}}, "###", True],
    ],
    indirect=["set_project_quota"],
    ids=["max_cpu", "max_storage", "max_memory", "max_vms"],
)
def test_project_quota_enforce_via_lifecycle_cloud(
    request,
    appliance,
    provider,
    new_user_project,
    set_project_quota,
    extra_msg,
    approve,
    custom_prov_data,
    prov_data,
    provisioning,
):
    """Test Project Quota in UI

    Polarion:
        assignee: ghubale
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/8h
        tags: quota
        testSteps:
            1. Create a project
            2. Assign quota to project
            3. Provision instance over the assigned project's quota
            4. Check whether quota is exceeded or not
    """
    with new_user_project:
        recursive_update(prov_data, custom_prov_data)
        recursive_update(
            prov_data,
            {
                "request": {
                    "email": fauxfactory.gen_email(),
                    "first_name": fauxfactory.gen_alphanumeric(),
                    "last_name": fauxfactory.gen_alphanumeric(),
                    "manager_name": "{name}".format(name=fauxfactory.gen_alphanumeric()),
                }
            },
        )
        prov_data.update({"template_name": provisioning["image"]["name"]})
        request_description = "Provision from [{template}] to [{vm}{msg}]".format(
            template=provisioning["image"]["name"], vm=prov_data['catalog']['vm_name'],
            msg=extra_msg)
        appliance.collections.cloud_instances.create(
            prov_data['catalog']['vm_name'],
            provider,
            prov_data,
            auto_approve=approve,
            override=True,
            request_description=request_description,
        )
        provision_request = appliance.collections.requests.instantiate(request_description)
        provision_request.wait_for_request(method="ui")
        request.addfinalizer(provision_request.remove_request)
        assert provision_request.row.reason.text == "Quota Exceeded"
