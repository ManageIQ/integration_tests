import random
import re

import fauxfactory
import pytest
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider.azure import AzureProvider
from cfme.fixtures.service_fixtures import create_catalog_item
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.update import update


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
        name=fauxfactory.gen_alphanumeric(12, start="tenant_"),
        description=fauxfactory.gen_alphanumeric(15, start="tenant_des_"),
        parent=collection.get_root_tenant(),
    )
    yield tenant
    if tenant.exists:
        tenant.delete()


@pytest.fixture(scope="module")
def new_child(appliance, new_tenant):
    """The fixture creates new child tenant"""
    child_tenant = appliance.collections.tenants.create(
        name=fauxfactory.gen_alphanumeric(12, start="tenant_"),
        description=fauxfactory.gen_alphanumeric(15, start="tenant_des_"),
        parent=new_tenant,
    )
    yield child_tenant
    if child_tenant.exists:
        child_tenant.delete()


@pytest.fixture(scope="module")
def new_group_child(appliance, new_child, new_tenant):
    """This fixture creates new group assigned by new child tenant"""
    group = appliance.collections.groups.create(
        description=fauxfactory.gen_alphanumeric(start="group_"),
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
        name=fauxfactory.gen_alphanumeric(start="user_").lower(),
        credential=Credential(principal=fauxfactory.gen_alphanumeric(start="uid"),
                              secret=fauxfactory.gen_alphanumeric(start="pwd_")),
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
        name=fauxfactory.gen_alphanumeric(12, start="project_"),
        description=fauxfactory.gen_alphanumeric(15, start="project_desc"),
        parent=collection.get_root_tenant(),
    )
    yield project
    if project.exists:
        project.delete()


@pytest.fixture(scope="module")
def new_group_project(appliance, new_project):
    """This fixture creates new group and assigned by new project"""
    group = appliance.collections.groups.create(
        description=fauxfactory.gen_alphanumeric(start="group_"),
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
        name=fauxfactory.gen_alphanumeric(start="user_").lower(),
        credential=Credential(principal=fauxfactory.gen_alphanumeric(start="uid"),
                              secret=fauxfactory.gen_alphanumeric(start="pwd")),
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
                    "first_name": fauxfactory.gen_alphanumeric(start="first_"),
                    "last_name": fauxfactory.gen_alphanumeric(start="last_"),
                    "manager_name": fauxfactory.gen_alphanumeric(start="manager_"),
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
                    "first_name": fauxfactory.gen_alphanumeric(start="first_"),
                    "last_name": fauxfactory.gen_alphanumeric(start="last_"),
                    "manager_name": fauxfactory.gen_alphanumeric(start="manager_"),
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


@pytest.fixture
def admin_email(appliance):
    """Required for user quota tagging services to work, as it's mandatory for it's functioning."""
    user = appliance.collections.users
    admin = user.instantiate(name='Administrator')
    with update(admin):
        admin.email = fauxfactory.gen_email()
    yield
    with update(admin):
        admin.email = ''


@pytest.fixture(scope="module")
def automate_flavor_method(appliance, klass, namespace):
    """This fixture used to create automate method using following script"""
    script = """
                FLAVOR_CLASS = 'Flavor'.freeze\n
                begin\n
                    values_hash = {}\n
                    cloud_flavors = $evm.vmdb(FLAVOR_CLASS).all\n
                $evm.log("info", "Listing Root Object Attributes:")\n
                $evm.root.attributes.sort.each { |k, v| $evm.log("info", "\t#{k}: #{v}") }\n
                $evm.log("info", "===========================================")\n
                    unless cloud_flavors.empty?\n
                        cloud_flavors.each do |flavor|\n
                            values_hash[flavor.id] = flavor.name\n
                    end\n
                end\n
                list_values = {\n
                    'sort_by'    => :value,\n
                    'data_type'  => :string,\n
                    'required'   => true,\n
                    'values'     => values_hash\n
                }\n
                list_values.each { |key, value| $evm.object[key] = value }\n
                rescue => err\n
                  $evm.log(:error, "[#{err}]\n#{err.backtrace.join("\n")}")\n
                  exit MIQ_STOP\n
                end\n
    """
    schema_field = fauxfactory.gen_alphanumeric()
    klass.schema.add_fields({'name': schema_field, 'type': 'Method', 'data_type': 'String'})
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script=script
    )
    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={schema_field: {'value': method.name}}
    )
    yield instance
    instance.delete()
    method.delete()


@pytest.fixture
def set_roottenant_quota(request, appliance):
    field, value = request.param
    roottenant = appliance.collections.tenants.get_root_tenant()
    roottenant.set_quota(**{'{}_cb'.format(field): True, field: value})
    yield
    roottenant.set_quota(**{'{}_cb'.format(field): False})


@pytest.fixture(scope="module")
def dialog(appliance, automate_flavor_method):
    """This fixture is used to create dynamic service dialog"""
    data = {
        "buttons": "submit,cancel",
        "label": fauxfactory.gen_alphanumeric(20, start="flavour_dialog_"),
        "dialog_tabs": [
            {
                "display": 'edit',
                "label": "New Tab",
                "position": 0,
                "dialog_groups": [
                    {
                        "display": "edit",
                        "label": "New section",
                        "position": 0,
                        "dialog_fields": [
                            {
                                "name": "option_0_instance_type",
                                "description": "flavor_dialog",
                                "data_type": "string",
                                "display": "edit",
                                'display_method_options': {},
                                'required_method_options': {},
                                'default_value': '',
                                'values_method_options': {},
                                "required": True,
                                "label": "instance_type",
                                "dynamic": True,
                                'show_refresh_button': True,
                                'load_values_on_init': True,
                                'read_only': False,
                                'auto_refresh': False,
                                'visible': True,
                                "type": "DialogFieldDropDownList",
                                "resource_action": {
                                    "resource_type": "DialogField",
                                    "ae_namespace": automate_flavor_method.namespace.name,
                                    "ae_class": automate_flavor_method.klass.name,
                                    "ae_instance": automate_flavor_method.name,
                                },
                            },
                        ],
                    }
                ],
            }
        ],
    }
    dialog_rest = appliance.rest_api.collections.service_dialogs.action.create(**data)[0]
    yield appliance.collections.service_dialogs.instantiate(label=dialog_rest.label)
    dialog_rest.action.delete()


def get_quota_message(request, appliance, catalog, catalog_item_name, dialog_values=None):
    """Returns the quota requested by particular type of flavor type"""
    service_catalogs = ServiceCatalogs(appliance, catalog, catalog_item_name, dialog_values)
    service_catalogs.order()
    # nav to requests page to check quota validation
    request_description = 'Provisioning Service [{0}] from [{0}]'.format(catalog_item_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"
    last_message = provision_request.row.last_message.text
    result = re.findall(r'requested.*\w', last_message)

    # Service request needs to delete because we are not able to order same catalog item multiple
    # times using automation.
    delete_request = appliance.rest_api.collections.service_requests.get(
        description=request_description)
    delete_request.action.delete()

    return result


# first arg of parametrize is the list of fixture or parameter,
# second arg is a list of lists, with a test is to be generated
# indirect is the list where we define which fixture is to be passed values indirectly.
@pytest.mark.meta(blockers=[BZ(1704439)])
@pytest.mark.tier(1)
@pytest.mark.parametrize(
    ['set_roottenant_quota'],
    [
        [('storage', 0.001)]
    ],
    indirect=['set_roottenant_quota'],
    ids=['max_storage']
)
def test_custom_service_dialog_quota_flavors(request, provider, provisioning, dialog, catalog,
                                             appliance, admin_email, set_roottenant_quota):
    """Test quota with instance/flavor type in custom dialog

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.8
        casecomponent: Quota

    Bugzilla:
        1499193
        1581288
        1657628
    """
    catalog_item = create_catalog_item(appliance, provider, provisioning, dialog, catalog)
    request.addfinalizer(catalog_item.delete_if_exists)
    result = []

    # Fetching all the flavours related to particular provider and collecting two flavors randomly
    flavors = random.sample(appliance.rest_api.collections.flavors.all, 2)

    # Ordering service catalog item with different flavor types
    for flavor in flavors:
        flavor_type = {'option_0_instance_type': flavor.name}
        requested_storage = get_quota_message(
            request=request, appliance=appliance, catalog=catalog_item.catalog,
            catalog_item_name=catalog_item.name, dialog_values=flavor_type
        )
        result.append(requested_storage)

    # Checks if catalog item is ordered with different flavor by asserting requested storage of
    # different flavors which should not match
    assert result[0] != result[1]
