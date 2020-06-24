import re

import fauxfactory
from widgetastic.utils import partial_match
from wrapanapi import VmState

from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.log import logger
from cfme.utils.rest import create_resource
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import wait_for

TEMPLATE_TORSO = """{
  "AWSTemplateFormatVersion" : "2010-09-09",
  "Description" : "AWS CloudFormation Sample Template Rails_Single_Instance.",

  "Parameters" : {
    "KeyName": {
      "Description" : "Name of an existing EC2 KeyPair to enable SSH access to the instances",
      "Type": "AWS::EC2::KeyPair::KeyName",
      "ConstraintDescription" : "must be the name of an existing EC2 KeyPair."
    }
  }
}
"""


def service_catalogs(request, appliance, num=5):
    """Create service catalogs using REST API."""
    scls_data = []
    for _ in range(num):
        scls_data.append({
            'name': fauxfactory.gen_alphanumeric(start="cat_"),
            'description': 'my catalog',
            'service_templates': []
        })

    return _creating_skeleton(request, appliance, 'service_catalogs', scls_data, col_action='add')


def service_catalog_obj(request, appliance):
    """Return service catalog object."""
    rest_catalog = service_catalogs(request, appliance, num=1)[0]
    return appliance.collections.catalogs.instantiate(name=rest_catalog.name,
                                                      description=rest_catalog.description)


def categories(request, appliance, num=1):
    ctg_data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric().lower()
        ctg_data.append({
            'name': f'test_category_{uniq}',
            'description': f'test_category_{uniq}'
        })

    return _creating_skeleton(request, appliance, 'categories', ctg_data)


def tags(request, appliance, categories):
    # Category id, href or name needs to be specified for creating a new tag resource
    tags = []
    for index, ctg in enumerate(categories):
        uniq = fauxfactory.gen_alphanumeric().lower()
        refs = [{'id': ctg.id}, {'href': ctg.href}, {'name': ctg.name}]
        tags.append({
            'name': f'test_tag_{uniq}',
            'description': f'test_tag_{uniq}',
            'category': refs[index % 3]
        })

    return _creating_skeleton(request, appliance, 'tags', tags, substr_search=True)


def dialog_rest(request, appliance):
    """Creates service dialog using REST API."""
    uid = fauxfactory.gen_alphanumeric()
    data = {
        "description": f"my dialog {uid}",
        "label": uid,
        "buttons": "submit,cancel",
        "dialog_tabs": [{
            "description": f"my tab desc {uid}",
            "position": 0,
            "label": f"tab_{uid}",
            "display": "edit",
            "dialog_groups": [{
                "description": f"my box desc {uid}",
                "label": f"box_{uid}",
                "display": "edit",
                "position": 0,
                "dialog_fields": [{
                    "name": "service_name",
                    "description": f"my ele desc {uid}",
                    "label": f"ele_{uid}",
                    "data_type": "string",
                    "display": "edit",
                    "required": False,
                    "default_value": uid,
                    "options": {
                        "protected": False
                    },
                    "position": 0,
                    "dynamic": False,
                    "read_only": False,
                    "visible": True,
                    "type": "DialogFieldTextBox",
                    "resource_action": {
                        "resource_type": "DialogField",
                        "ae_attributes": {}
                    }
                }]
            }]
        }]
    }

    service_dialog = _creating_skeleton(request, appliance, "service_dialogs", [data])
    return service_dialog[0]


def dialog(request, appliance):
    """Returns service dialog object."""
    rest_resource = dialog_rest(request, appliance)
    service_dialogs = appliance.collections.service_dialogs
    service_dialog = service_dialogs.instantiate(
        label=rest_resource.label,
        description=rest_resource.description)
    return service_dialog


def services(
    request, appliance, provider, service_dialog=None, service_catalog=None, service_template=None
):
    """
    The attempt to add the service entities via web
    """
    if not service_template:
        service_template = service_templates_ui(
            request,
            appliance,
            service_dialog=service_dialog,
            service_catalog=service_catalog,
            provider=provider,
            num=1
        )[0]

    service_catalog = appliance.rest_api.get_entity(
        'service_catalogs',
        service_template.service_template_catalog_id
    )
    template_subcollection = appliance.rest_api.get_entity(
        service_catalog.service_templates,
        service_template.id
    )
    template_subcollection.action.order()
    results = appliance.rest_api.response.json()
    service_request = appliance.rest_api.get_entity('service_requests', results['id'])

    def _order_finished():
        service_request.reload()
        return service_request.request_state.lower() == 'finished'

    wait_for(_order_finished, num_sec=2000, delay=10)
    assert 'error' not in service_request.message.lower(), ('Provisioning failed: `{}`'
                                                            .format(service_request.message))

    service_name = get_dialog_service_name(appliance, service_request, service_template.name)
    assert f'[{service_name}]' in service_request.message
    provisioned_service = appliance.rest_api.collections.services.get(
        service_template_id=service_template.id)

    @request.addfinalizer
    def _finished():
        try:
            provisioned_service.action.delete()
        except Exception:
            # service can be deleted by test
            logger.warning(f'Failed to delete service `{service_name}`.')

    # tests expect iterable
    return [provisioned_service]


def rates(request, appliance, num=3):
    chargeback = appliance.rest_api.collections.chargebacks.get(rate_type='Compute')
    data = []
    for _ in range(num):
        req = {'description': fauxfactory.gen_alphanumeric(15, start="test_rate_"),
               'source': 'allocated',
               'group': 'cpu',
               'per_time': 'daily',
               'per_unit': 'megahertz',
               'chargeback_rate_id': chargeback.id,
               'chargeable_field_id': chargeback.id}
        data.append(req)

    return _creating_skeleton(request, appliance, 'rates', data)


def vm(request, provider, appliance, **kwargs):
    vm_name = kwargs.pop("name", fauxfactory.gen_alphanumeric(length=18, start="test_rest_vm_"))
    provider_rest = appliance.rest_api.collections.providers.get(name=provider.name)
    vm = deploy_template(provider.key, vm_name)

    @request.addfinalizer
    def _finished():
        try:
            vm.cleanup()
        except Exception:
            # vm can be deleted/retired by test
            logger.warning("Failed to delete vm %r", vm)

    provider_rest.action.refresh()
    wait_for(
        lambda: appliance.rest_api.collections.vms.find_by(name=vm_name) or False,
        num_sec=600, delay=5)
    return vm_name


def service_templates_ui(request, appliance, service_dialog=None, service_catalog=None,
        provider=None, num=4):
    if not service_dialog:
        service_dialog = dialog(request, appliance)
    if not service_catalog:
        service_catalog = service_catalog_obj(request, appliance)

    cat_items_col = appliance.collections.catalog_items
    catalog_item_type = provider.catalog_item_type if provider else cat_items_col.GENERIC

    new_names = []
    for _ in range(num):
        if provider:
            template, host, datastore, vlan = list(map(
                provider.data.get('provisioning').get,
                ('template', 'host', 'datastore', 'vlan')))

            vm_name = fauxfactory.gen_alphanumeric(15, start="test_rest_")

            provisioning_data = {
                'catalog': {'catalog_name': {'name': template},
                            'vm_name': vm_name},
                'environment': {'host_name': {'name': host},
                                'datastore_name': {'name': datastore},
                                },
                'network': {},
            }

            if provider.one_of(RHEVMProvider):
                provisioning_data['catalog']['provision_type'] = 'Native Clone'
                provisioning_data['network']['vlan'] = partial_match(vlan)
            elif provider.one_of(VMwareProvider):
                provisioning_data['catalog']['provision_type'] = 'VMware'
                provisioning_data['network']['vlan'] = partial_match(vlan)

        new_name = fauxfactory.gen_alphanumeric(15, start="cat_item_")
        new_names.append(new_name)
        cat_items_col.create(
            catalog_item_type,
            name=new_name,
            description='my catalog',
            display_in=True,
            catalog=service_catalog,
            dialog=service_dialog,
            prov_data=provisioning_data
        )

    collection = appliance.rest_api.collections.service_templates

    for new_name in new_names:
        wait_for(lambda: collection.find_by(name=new_name) or False, num_sec=180, delay=10)

    s_tpls = [ent for ent in collection if ent.name in new_names]

    @request.addfinalizer
    def _finished():
        collection.reload()
        to_delete = [ent for ent in collection if ent.name in new_names]
        if to_delete:
            collection.action.delete(*to_delete)

    return s_tpls


def service_templates_rest(request, appliance, service_dialog=None, service_catalog=None, num=4):
    if not service_dialog:
        service_dialog = dialog(request, appliance)
    if not service_catalog:
        service_catalog = service_catalog_obj(request, appliance)

    catalog_id = appliance.rest_api.collections.service_catalogs.get(name=service_catalog.name).id
    dialog_id = appliance.rest_api.collections.service_dialogs.get(label=service_dialog.label).id

    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(5)
        data.append({
            "name": f'item_{uniq}',
            "description": f"my catalog {uniq}",
            "service_type": "atomic",
            "prov_type": "generic",
            "display": True,
            "service_template_catalog_id": catalog_id,
            "config_info": {
                "provision": {
                    "dialog_id": dialog_id,
                    "fqname": "/Service/Provisioning/StateMachines/"
                              "ServiceProvision_Template/CatalogItemInitialization"
                },
                "retirement": {
                    "dialog_id": dialog_id,
                    "fqname": "/Service/Retirement/StateMachines/ServiceRetirement/Default"
                },
            }
        })

    return _creating_skeleton(request, appliance, "service_templates", data)


def service_templates(request, appliance, service_dialog=None, service_catalog=None, num=4):
    return service_templates_rest(
        request, appliance, service_dialog=service_dialog, service_catalog=service_catalog, num=num)


def automation_requests_data(vm, requests_collection=False, approve=True, num=4):
    # for creating automation request using /api/automation_requests
    automation_requests_col = {
        "uri_parts": {
            "namespace": "System",
            "class": "Request",
            "instance": "InspectME",
            "message": "create",
        },
        "parameters": {
            "vm_name": vm,
        },
        "requester": {
            "auto_approve": approve
        }
    }
    # for creating automation request using /api/requests
    requests_col = {
        "options": {
            "request_type": "automation",
            "message": "create",
            "namespace": "System",
            "class_name": "Request",
            "instance_name": "InspectME",
            "attrs": {
                "vm_name": vm,
                "userid": "admin"
            }
        },
        "requester": {
            "user_name": "admin"
        },
        "auto_approve": approve
    }
    data = requests_col if requests_collection else automation_requests_col
    return [data for _ in range(num)]


def groups(request, appliance, role, num=1, **kwargs):
    tenant = kwargs.pop("tenant", appliance.rest_api.collections.tenants.get(name="My Company"))
    if num > 1 and kwargs:
        raise Exception("kwargs cannot be used when num is more than 1")

    data = []
    for _ in range(num):
        data.append(
            {
                "description": kwargs.get(
                    "description",
                    fauxfactory.gen_alphanumeric(25, start="group_description_"),
                ),
                "role": {"href": role.href},
                "tenant": {"href": tenant.href},
            }
        )

    groups = _creating_skeleton(request, appliance, "groups", data)
    if num == 1:
        return groups.pop()
    return groups


def roles(request, appliance, num=1, **kwargs):
    if num > 1 and kwargs:
        raise Exception("kwargs cannot be used when num is more than 1")

    data = []
    for _ in range(num):
        data.append(
            {
                "name": kwargs.get(
                    "name", fauxfactory.gen_alphanumeric(15, start="role_name_")
                ),
                "features": kwargs.get(
                    "features",
                    [
                        {"identifier": "vm_explorer"},
                        {"identifier": "ems_infra_tag"},
                        {"identifier": "miq_report_run"},
                    ],
                ),
            }
        )

    roles = _creating_skeleton(request, appliance, "roles", data)
    if num == 1:
        return roles.pop()
    return roles


def copy_role(appliance, orig_name, new_name=None):
    orig_role = appliance.rest_api.collections.roles.get(name=orig_name)
    orig_features = orig_role._data.get('features')
    orig_settings = orig_role._data.get('settings')
    if not orig_features and hasattr(orig_role, 'features'):
        features_subcol = orig_role.features
        features_subcol.reload()
        orig_features = features_subcol._data.get('resources')
    if not orig_features:
        raise NotImplementedError('Role copy is not implemented for this version.')
    new_role = appliance.rest_api.collections.roles.action.create(
        name=new_name or fauxfactory.gen_alphanumeric(12, start="EvmRole-"),
        features=orig_features,
        settings=orig_settings
    )
    return new_role[0]


def tenants(request, appliance, num=1, **kwargs):
    parent = kwargs.pop(
        "parent", appliance.rest_api.collections.tenants.get(name="My Company")
    )

    if num > 1 and kwargs:
        raise Exception("kwargs cannot be used when num is more than 1")

    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric()
        data.append({
            'description': kwargs.get("description", f'test_tenants_{uniq}'),
            'name': kwargs.get("name", f'test_tenants_{uniq}'),
            'divisible': kwargs.get("divisible", 'true'),
            'use_config_for_attributes': kwargs.get("use_config_for_attributes", 'false'),
            'parent': {'href': parent.href}
        })

    tenants = _creating_skeleton(request, appliance, 'tenants', data)
    if num == 1:
        return tenants.pop()
    return tenants


def users(request, appliance, num=1, **kwargs):
    if num > 1 and kwargs:
        raise Exception("kwargs cannot be used when num is more than 1")

    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(4).lower()
        data.append(
            {
                "userid": kwargs.get("userid", f"user_{uniq}"),
                "name": kwargs.get("name", f"name_{uniq}"),
                "password": kwargs.get("password", fauxfactory.gen_alphanumeric()),
                "email": kwargs.get("email", f"{uniq}@example.com"),
                "group": {"description": kwargs.get("group", "EvmGroup-user_self_service")},
            }
        )

    users = _creating_skeleton(request, appliance, "users", data)
    return users, data


def _creating_skeleton(request, appliance, col_name, col_data, col_action='create',
        substr_search=False):

    entities = create_resource(
        appliance.rest_api, col_name, col_data, col_action=col_action, substr_search=substr_search)

    # make sure the original list of `entities` is preserved for cleanup
    original_entities = list(entities)

    @request.addfinalizer
    def _finished():
        collection = getattr(appliance.rest_api.collections, col_name)
        collection.reload()
        ids = [e.id for e in original_entities]
        delete_entities = [e for e in collection if e.id in ids]
        if delete_entities:
            collection.action.delete(*delete_entities)

    return entities


def mark_vm_as_template(appliance, provider, vm_name):
    """
        Function marks vm as template via mgmt and returns template Entity
        Usage:
            mark_vm_as_template(appliance, provider, vm_name)
    """
    t_vm = appliance.rest_api.collections.vms.get(name=vm_name)
    t_vm.action.stop()
    vm_mgmt = provider.mgmt.get_vm(vm_name)
    vm_mgmt.ensure_state(VmState.STOPPED, timeout=1000)
    vm_mgmt.mark_as_template()

    wait_for(
        lambda: appliance.rest_api.collections.templates.find_by(name=vm_name).subcount != 0,
        num_sec=700, delay=15)
    return appliance.rest_api.collections.templates.get(name=vm_name)


def orchestration_templates(request, appliance, num=2):
    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(5)
        data.append({
            'name': f'test_{uniq}',
            'description': f'Test Template {uniq}',
            'type': 'ManageIQ::Providers::Amazon::CloudManager::OrchestrationTemplate',
            'orderable': False,
            'draft': False,
            'content': TEMPLATE_TORSO.replace('CloudFormation', uniq)})

    return _creating_skeleton(request, appliance, 'orchestration_templates', data)


def arbitration_profiles(request, appliance, provider, num=2):
    r_provider = appliance.rest_api.collections.providers.get(name=provider.name)
    data = []
    providers = [{'id': r_provider.id}, {'href': r_provider.href}]
    for index in range(num):
        data.append({
            'name': fauxfactory.gen_alphanumeric(20, start="test_settings_"),
            'provider': providers[index % 2]
        })

    return _creating_skeleton(request, appliance, 'arbitration_profiles', data)


def conditions(request, appliance, num=2):
    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(5)
        data_dict = {
            'name': f'test_condition_{uniq}',
            'description': f'Test Condition {uniq}',
            'expression': {'=': {'field': 'ContainerImage-architecture', 'value': 'dsa'}},
            'towhat': 'ExtManagementSystem'
        }
        if appliance.version < '5.10':
            data_dict["modifier"] = "allow"
        data.append(data_dict)

    return _creating_skeleton(request, appliance, 'conditions', data)


def policies(request, appliance, num=2):
    conditions_response = conditions(request, appliance, num=2)
    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(5)
        data.append({
            'name': f'test_policy_{uniq}',
            'description': f'Test Policy {uniq}',
            'mode': 'compliance',
            'towhat': 'ExtManagementSystem',
            'conditions_ids': [conditions_response[0].id, conditions_response[1].id],
            'policy_contents': [{
                'event_id': 2,
                'actions': [{'action_id': 1, 'opts': {'qualifier': 'failure'}}]
            }]
        })

    return _creating_skeleton(request, appliance, 'policies', data)


def get_dialog_service_name(appliance, service_request, *item_names):
    """
    Helper function, when tests need to determine a dialog service name.
    Service name is obtained by parsing it from the service request message.

    TODO: In gaprindashvili+ dialog service name is available in the service_request options,
    but currently no value is returned in the response.
    Use service_request options once it correctly returns the dialog service name.
    """
    def _regex_parse_name(items, message):
        for item in items:
            match = re.search(fr'\[({item}[0-9-]*)\] ', message)
            if match:
                return match.group(1)
            else:
                continue
        else:
            raise ValueError('Could not match name from items in given service request message')

    return _regex_parse_name(item_names, service_request.message)


def custom_button_sets(request, appliance, button_type, icon="fa-user", color="#4727ff", num=1):
    data = []
    for _ in range(num):
        data_dict = {
            "name": fauxfactory.gen_alphanumeric(start="grp_"),
            "description": fauxfactory.gen_alphanumeric(15, start="grp_desc_"),
            "set_data": {
                "button_icon": f"ff {icon}",
                "button_color": color,
                "display": True,
                "applies_to_class": button_type,
            },
        }
        data.append(data_dict)

    return _creating_skeleton(request, appliance, "custom_button_sets", data)


def custom_buttons(
    request, appliance, button_type, icon="fa-user", color="#4727ff", display=True, num=1
):
    data = []
    for _ in range(num):
        data_dict = {
            "applies_to_class": button_type,
            "description": fauxfactory.gen_alphanumeric(start="btn_"),
            "name": fauxfactory.gen_alphanumeric(12, start="btn_desc_"),
            "options": {
                "button_color": color,
                "button_icon": f"ff {icon}",
                "display": display,
            },
            "resource_action": {"ae_class": "PROCESS", "ae_namespace": "SYSTEM"},
            "visibility": {"roles": ["_ALL_"]},
        }
        data.append(data_dict)

    return _creating_skeleton(request, appliance, "custom_buttons", data)


def policy_profiles(request, appliance, num=2):
    data = []
    for _ in range(num):
        data.append(
            {
                "description": fauxfactory.gen_alpha(start="PP description ", length=17),
                "name": fauxfactory.gen_alpha(start="test_pp_name_", length=17),
            }
        )
    return _creating_skeleton(request, appliance, "policy_profiles", data)
