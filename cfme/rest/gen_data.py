# -*- coding: utf-8 -*-
import fauxfactory

from cfme.exceptions import OptionNotAvailable
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogItem
from fixtures.provider import setup_one_by_class_or_skip
from cfme.utils import version
from cfme.utils.log import logger
from cfme.utils.rest import get_vms_in_service
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import wait_for


_TEMPLATE_TORSO = """{
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


def service_catalogs(request, rest_api, num=5):
    """Create service catalogs using REST API."""
    scls_data = []
    for _ in range(num):
        scls_data.append({
            'name': 'cat_{}'.format(fauxfactory.gen_alphanumeric()),
            'description': 'my catalog',
            'service_templates': []
        })

    return _creating_skeleton(request, rest_api, 'service_catalogs', scls_data, col_action='add')


def service_catalog_obj(request, rest_api):
    """Return service catalog object."""
    rest_catalog = service_catalogs(request, rest_api, num=1)[0]
    return Catalog(name=rest_catalog.name, description=rest_catalog.description)


def categories(request, rest_api, num=1):
    ctg_data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric().lower()
        ctg_data.append({
            'name': 'test_category_{}'.format(uniq),
            'description': 'test_category_{}'.format(uniq)
        })

    return _creating_skeleton(request, rest_api, 'categories', ctg_data)


def tags(request, rest_api, categories):
    # Category id, href or name needs to be specified for creating a new tag resource
    tags = []
    for index, ctg in enumerate(categories):
        uniq = fauxfactory.gen_alphanumeric().lower()
        refs = [{'id': ctg.id}, {'href': ctg.href}, {'name': ctg.name}]
        tags.append({
            'name': 'test_tag_{}'.format(uniq),
            'description': 'test_tag_{}'.format(uniq),
            'category': refs[index % 3]
        })

    return _creating_skeleton(request, rest_api, 'tags', tags, substr_search=True)


def dialog_ui(appliance):
    """Creates service dialog using UI."""
    service_dialogs = appliance.collections.service_dialogs
    uid = fauxfactory.gen_alphanumeric()
    # ele_name has to be "service_name" so that we can override the service name generated
    # by provisioning as that name contains timestamp which is difficult to assert.
    # Also the dialog label and default text box should be same value = uid here.
    element_data = dict(
        ele_label="ele_{}".format(uid),
        ele_name="service_name",
        ele_desc="my ele desc {}".format(uid),
        choose_type="Text Box",
        default_text_box=uid
    )
    service_dialog = service_dialogs.create(
        label=uid,
        description="my dialog {}".format(uid),
        submit=True,
        cancel=True
    )
    tab = service_dialog.tabs.create(
        tab_label="tab_{}".format(uid),
        tab_desc="my tab desc {}".format(uid)
    )
    box = tab.boxes.create(
        box_label="box_{}".format(uid),
        box_desc="my box desc {}".format(uid)
    )
    box.elements.create(element_data=[element_data])
    return service_dialog


def dialog_rest(request, rest_api):
    """Creates service dialog using REST API."""
    uid = fauxfactory.gen_alphanumeric()
    data = {
        "description": "my dialog {}".format(uid),
        "label": uid,
        "buttons": "submit,cancel",
        "dialog_tabs": [{
            "description": "my tab desc {}".format(uid),
            "position": 0,
            "label": "tab_{}".format(uid),
            "display": "edit",
            "dialog_groups": [{
                "description": "my box desc {}".format(uid),
                "label": "box_{}".format(uid),
                "display": "edit",
                "position": 0,
                "dialog_fields": [{
                    "name": "service_name",
                    "description": "my ele desc {}".format(uid),
                    "label": "ele_{}".format(uid),
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

    service_dialog = _creating_skeleton(request, rest_api, "service_dialogs", [data])
    return service_dialog[0]


def dialog(request, appliance):
    """Returns service dialog object."""
    # action "create" is not supported in version < 5.8, use UI
    if version.current_version() < '5.8':
        return dialog_ui(appliance)

    # setup dialog using REST API
    rest_resource = dialog_rest(request, appliance.rest_api)
    service_dialogs = appliance.collections.service_dialogs
    service_dialog = service_dialogs.instantiate(
        label=rest_resource.label,
        description=rest_resource.description,
        submit=True,
        cancel=True
    )
    return service_dialog


def services(request, appliance, a_provider, service_dialog=None, service_catalog=None):
    """
    The attempt to add the service entities via web
    """
    service_template = service_templates_ui(
        request,
        appliance,
        service_dialog=service_dialog,
        service_catalog=service_catalog,
        a_provider=a_provider,
        num=1
    )

    service_template = service_template[0]
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
    assert 'error' not in service_request.message.lower(), \
        'Provisioning failed with the message `{}`'.format(service_request.message)

    service_name = str(service_request.options['dialog']['dialog_service_name'])
    assert '[{}]'.format(service_name) in service_request.message
    provisioned_service = appliance.rest_api.collections.services.get(name=service_name)

    @request.addfinalizer
    def _finished():
        try:
            provisioned_service.action.delete()
        except Exception:
            # service can be deleted by test
            logger.warning('Failed to delete service `{}`.'.format(service_name))

    # tests expect iterable
    return [provisioned_service]


def service_data(request, appliance, a_provider, service_dialog=None, service_catalog=None):
    prov_service = services(request, appliance, a_provider, service_dialog, service_catalog).pop()
    prov_vm = get_vms_in_service(appliance.rest_api, prov_service).pop()
    return {'service_name': prov_service.name, 'vm_name': prov_vm.name}


def rates(request, rest_api, num=3):
    chargeback = rest_api.collections.chargebacks.get(rate_type='Compute')
    data = []
    for _ in range(num):
        req = {
            'description': 'test_rate_{}'.format(fauxfactory.gen_alphanumeric()),
            'source': 'allocated',
            'group': 'cpu',
            'per_time': 'daily',
            'per_unit': 'megahertz',
            'chargeback_rate_id': chargeback.id
        }
        if version.current_version() >= '5.8':
            req['chargeable_field_id'] = chargeback.id
        data.append(req)

    return _creating_skeleton(request, rest_api, 'rates', data)


def a_provider(request):
    return setup_one_by_class_or_skip(request, InfraProvider)


def vm(request, a_provider, rest_api):
    provider_rest = rest_api.collections.providers.get(name=a_provider.name)
    vm_name = deploy_template(
        a_provider.key,
        'test_rest_vm_{}'.format(fauxfactory.gen_alphanumeric(length=4)))

    @request.addfinalizer
    def _finished():
        try:
            a_provider.mgmt.delete_vm(vm_name)
        except Exception:
            # vm can be deleted/retired by test
            logger.warning("Failed to delete vm '{}'.".format(vm_name))

    provider_rest.action.refresh()
    wait_for(
        lambda: rest_api.collections.vms.find_by(name=vm_name) or False,
        num_sec=600, delay=5)
    return vm_name


def service_templates_ui(request, appliance, service_dialog=None, service_catalog=None,
        a_provider=None, num=4):
    if not service_dialog:
        service_dialog = dialog(request, appliance)
    if not service_catalog:
        service_catalog = service_catalog_obj(request, appliance.rest_api)

    catalog_item_type = 'Generic'
    provisioning_args = {}

    catalog_items = []
    new_names = []
    for _ in range(num):
        if a_provider:
            template, host, datastore, vlan, catalog_item_type = map(
                a_provider.data.get('provisioning').get,
                ('template', 'host', 'datastore', 'vlan', 'catalog_item_type'))

            vm_name = 'test_rest_{}'.format(fauxfactory.gen_alphanumeric())

            provisioning_data = {
                'catalog': {'vm_name': vm_name,
                            },
                'environment': {'host_name': {'name': host},
                                'datastore_name': {'name': datastore},
                                },
                'network': {},
            }

            if a_provider.one_of(RHEVMProvider):
                provisioning_data['catalog']['provision_type'] = 'Native Clone'
                provisioning_data['network']['vlan'] = vlan
                catalog_item_type = 'RHEV'
            elif a_provider.one_of(VMwareProvider):
                provisioning_data['catalog']['provision_type'] = 'VMware'
                provisioning_data['network']['vlan'] = vlan

            provisioning_args = dict(
                catalog_name=template,
                provider=a_provider,
                prov_data=provisioning_data
            )

        new_name = 'item_{}'.format(fauxfactory.gen_alphanumeric())
        new_names.append(new_name)
        catalog_items.append(
            CatalogItem(
                item_type=catalog_item_type,
                name=new_name,
                description='my catalog',
                display_in=True,
                catalog=service_catalog,
                dialog=service_dialog,
                **provisioning_args
            )
        )

    for catalog_item in catalog_items:
        catalog_item.create()

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
        service_catalog = service_catalog_obj(request, appliance.rest_api)

    catalog_id = appliance.rest_api.collections.service_catalogs.get(name=service_catalog.name).id
    dialog_id = appliance.rest_api.collections.service_dialogs.get(label=service_dialog.label).id

    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(5)
        data.append({
            "name": 'item_{}'.format(uniq),
            "description": "my catalog {}".format(uniq),
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

    return _creating_skeleton(request, appliance.rest_api, "service_templates", data)


def service_templates(request, appliance, service_dialog=None, service_catalog=None, num=4):
    tmplt = service_templates_ui if version.current_version() < '5.8' else service_templates_rest
    return tmplt(
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


def groups(request, rest_api, role, tenant, num=1):
    data = []
    for _ in range(num):
        data.append({
            "description": "group_description_{}".format(fauxfactory.gen_alphanumeric()),
            "role": {"href": role.href},
            "tenant": {"href": tenant.href}
        })

    groups = _creating_skeleton(request, rest_api, "groups", data)
    if num == 1:
        return groups.pop()
    return groups


def roles(request, rest_api, num=1):
    data = []
    for _ in range(num):
        data.append({"name": "role_name_{}".format(fauxfactory.gen_alphanumeric())})

    roles = _creating_skeleton(request, rest_api, "roles", data)
    if num == 1:
        return roles.pop()
    return roles


def copy_role(rest_api, orig_name, new_name=None):
    orig_role = rest_api.collections.roles.get(name=orig_name)
    orig_features = orig_role._data.get('features')
    orig_settings = orig_role._data.get('settings')
    if not orig_features and hasattr(orig_role, 'features'):
        features_subcol = orig_role.features
        features_subcol.reload()
        orig_features = features_subcol._data.get('resources')
    if not orig_features:
        raise NotImplementedError('Role copy is not implemented for this version.')
    new_role = rest_api.collections.roles.action.create(
        name=new_name or 'EvmRole-{}'.format(fauxfactory.gen_alphanumeric()),
        features=orig_features,
        settings=orig_settings
    )
    return new_role[0]


def tenants(request, rest_api, num=1):
    parent = rest_api.collections.tenants.get(name='My Company')
    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric()
        data.append({
            'description': 'test_tenants_{}'.format(uniq),
            'name': 'test_tenants_{}'.format(uniq),
            'divisible': 'true',
            'use_config_for_attributes': 'false',
            'parent': {'href': parent.href}
        })

    tenants = _creating_skeleton(request, rest_api, 'tenants', data)
    if num == 1:
        return tenants.pop()
    return tenants


def users(request, rest_api, num=1):
    data = []
    for _ in range(num):
        data.append({
            "userid": "user_{}".format(fauxfactory.gen_alphanumeric(3)),
            "name": "name_{}".format(fauxfactory.gen_alphanumeric()),
            "password": "pass_{}".format(fauxfactory.gen_alphanumeric(3)),
            "group": {"description": "EvmGroup-user"}
        })

    users = _creating_skeleton(request, rest_api, "users", data)
    if num == 1:
        return users.pop()
    return users


def _creating_skeleton(request, rest_api, col_name, col_data, col_action='create',
        substr_search=False):
    collection = getattr(rest_api.collections, col_name)
    try:
        action = getattr(collection.action, col_action)
    except AttributeError:
        raise OptionNotAvailable(
            "Action `{}` for {} is not implemented in this version".format(col_action, col_name))

    entities = action(*col_data)
    action_response = rest_api.response
    search_str = '%{}%' if substr_search else '{}'
    for entity in col_data:
        if entity.get('name'):
            wait_for(lambda: collection.find_by(
                name=search_str.format(entity.get('name'))) or False, num_sec=180, delay=10)
        elif entity.get('description'):
            wait_for(lambda: collection.find_by(
                description=search_str.format(entity.get('description'))) or False,
                num_sec=180, delay=10)
        else:
            raise NotImplementedError

    # make sure the original list of `entities` is preserved for cleanup
    original_entities = list(entities)

    @request.addfinalizer
    def _finished():
        collection.reload()
        ids = [e.id for e in original_entities]
        delete_entities = [e for e in collection if e.id in ids]
        if delete_entities:
            collection.action.delete(*delete_entities)

    # make sure action response is preserved
    rest_api.response = action_response
    return entities


def mark_vm_as_template(rest_api, provider, vm_name):
    """
        Function marks vm as template via mgmt and returns template Entity
        Usage:
            mark_vm_as_template(rest_api, provider, vm_name)
    """
    t_vm = rest_api.collections.vms.get(name=vm_name)
    t_vm.action.stop()
    provider.mgmt.wait_vm_stopped(vm_name=vm_name, num_sec=1000)

    provider.mgmt.mark_as_template(vm_name)

    wait_for(
        lambda: rest_api.collections.templates.find_by(name=vm_name).subcount != 0,
        num_sec=700, delay=15)
    return rest_api.collections.templates.get(name=vm_name)


def arbitration_settings(request, rest_api, num=2):
    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(5)
        data.append({
            'name': 'test_settings_{}'.format(uniq),
            'display_name': 'Test Settings {}'.format(uniq)})

    return _creating_skeleton(request, rest_api, 'arbitration_settings', data)


def orchestration_templates(request, rest_api, num=2):
    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(5)
        data.append({
            'name': 'test_{}'.format(uniq),
            'description': 'Test Template {}'.format(uniq),
            'type': 'OrchestrationTemplateCfn',
            'orderable': False,
            'draft': False,
            'content': _TEMPLATE_TORSO.replace('CloudFormation', uniq)})

    return _creating_skeleton(request, rest_api, 'orchestration_templates', data)


def arbitration_profiles(request, rest_api, a_provider, num=2):
    provider = rest_api.collections.providers.get(name=a_provider.name)
    data = []
    providers = [{'id': provider.id}, {'href': provider.href}]
    for index in range(num):
        data.append({
            'name': 'test_settings_{}'.format(fauxfactory.gen_alphanumeric(5)),
            'provider': providers[index % 2]
        })

    return _creating_skeleton(request, rest_api, 'arbitration_profiles', data)


def arbitration_rules(request, rest_api, num=2):
    data = []
    for _ in range(num):
        data.append({
            'description': 'test admin rule {}'.format(fauxfactory.gen_alphanumeric(5)),
            'operation': 'inject',
            'expression': {'EQUAL': {'field': 'User-userid', 'value': 'admin'}}
        })

    return _creating_skeleton(request, rest_api, 'arbitration_rules', data)


def blueprints(request, rest_api, num=2):
    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(5)
        data.append({
            'name': 'test_blueprint_{}'.format(uniq),
            'description': 'Test Blueprint {}'.format(uniq),
            'ui_properties': {
                'service_catalog': {},
                'service_dialog': {},
                'automate_entrypoints': {},
                'chart_data_model': {}
            }
        })

    return _creating_skeleton(request, rest_api, 'blueprints', data)


def conditions(request, rest_api, num=2):
    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(5)
        data.append({
            'name': 'test_condition_{}'.format(uniq),
            'description': 'Test Condition {}'.format(uniq),
            'expression': {'=': {'field': 'ContainerImage-architecture', 'value': 'dsa'}},
            'towhat': 'ExtManagementSystem',
            'modifier': 'allow'
        })

    return _creating_skeleton(request, rest_api, 'conditions', data)


def policies(request, rest_api, num=2):
    conditions_response = conditions(request, rest_api, num=2)
    data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(5)
        data.append({
            'name': 'test_policy_{}'.format(uniq),
            'description': 'Test Policy {}'.format(uniq),
            'mode': 'compliance',
            'towhat': 'ManageIQ::Providers::Redhat::InfraManager',
            'conditions_ids': [conditions_response[0].id, conditions_response[1].id],
            'policy_contents': [{
                'event_id': 2,
                'actions': [{'action_id': 1, 'opts': {'qualifier': 'failure'}}]
            }]
        })

    return _creating_skeleton(request, rest_api, 'policies', data)
