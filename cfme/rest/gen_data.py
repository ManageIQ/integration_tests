# -*- coding: utf-8 -*-
import fauxfactory

from cfme.automate.service_dialogs import ServiceDialog
from cfme.exceptions import OptionNotAvailable
from cfme.infrastructure.provider import InfraProvider
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from fixtures.provider import setup_one_by_class_or_skip
from utils.virtual_machines import deploy_template
from utils.wait import wait_for
from utils.log import logger
from utils import version


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
    scls_data = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric()
        scls_data.append({
            'name': 'name_{}'.format(uniq),
            'description': 'description_{}'.format(uniq),
            'service_templates': []
        })

    return _creating_skeleton(request, rest_api, 'service_catalogs', scls_data, col_action='add')


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

    return _creating_skeleton(request, rest_api, 'tags', tags)


def dialog():
    dialog = "dialog_{}".format(fauxfactory.gen_alphanumeric())
    element_data = dict(
        ele_label="ele_{}".format(fauxfactory.gen_alphanumeric()),
        ele_name=fauxfactory.gen_alphanumeric(),
        ele_desc="my ele desc",
        choose_type="Text Box",
        default_text_box="default value"
    )
    service_dialog = ServiceDialog(
        label=dialog,
        description="my dialog",
        submit=True,
        cancel=True,
        tab_label="tab_{}".format(fauxfactory.gen_alphanumeric()),
        tab_desc="my tab desc",
        box_label="box_{}".format(fauxfactory.gen_alphanumeric()),
        box_desc="my box desc")
    service_dialog.create(element_data)
    return service_dialog


def service_data(request, rest_api, a_provider, dialog, service_catalogs):
    """
    The attempt to add the service entities via web
    """
    template, host, datastore, vlan, catalog_item_type = map(
        a_provider.data.get('provisioning').get,
        ('template', 'host', 'datastore', 'vlan', 'catalog_item_type'))

    provisioning_data = {
        'vm_name': 'test_rest_{}'.format(fauxfactory.gen_alphanumeric()),
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]}
    }

    if a_provider.type == 'rhevm':
        provisioning_data['provision_type'] = 'Native Clone'
        provisioning_data['vlan'] = vlan
        catalog_item_type = 'RHEV'
    elif a_provider.type == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'
        provisioning_data['vlan'] = vlan

    vm_name = version.pick({
        version.LOWEST: provisioning_data['vm_name'] + '_0001',
        '5.7': provisioning_data['vm_name'] + '0001'})

    catalog = service_catalogs[0].name
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
                               description='my catalog', display_in=True,
                               catalog=catalog,
                               dialog=dialog.label,
                               catalog_name=template,
                               provider=a_provider,
                               prov_data=provisioning_data)

    catalog_item.create()
    service_catalogs = ServiceCatalogs(catalog_item.name)
    service_catalogs.order()
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, _ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=2000, delay=60)
    assert row.request_state.text == 'Finished'

    @request.addfinalizer
    def _finished():
        try:
            a_provider.mgmt.delete_vm(vm_name)
        except Exception:
            # vm can be deleted/retired by test
            logger.warning("Failed to delete vm '{}'.".format(vm_name))
        try:
            rest_api.collections.services.get(name=catalog_item.name).action.delete()
        except ValueError:
            # service can be deleted by test
            logger.warning("Failed to delete service '{}'.".format(catalog_item.name))

    return {'service_name': catalog_item.name, 'vm_name': vm_name}


def services(request, rest_api, a_provider, dialog, service_catalogs):
    new_service = service_data(request, rest_api, a_provider, dialog, service_catalogs)
    rest_service = rest_api.collections.services.get(name=new_service['service_name'])
    # tests expect iterable
    return [rest_service]


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
        lambda: len(rest_api.collections.vms.find_by(name=vm_name)) > 0,
        num_sec=600, delay=5)
    return vm_name


def service_templates(request, rest_api, dialog, num=4):
    catalog_items = []
    new_names = []
    for _ in range(num):
        new_name = 'item_{}'.format(fauxfactory.gen_alphanumeric())
        new_names.append(new_name)
        catalog_items.append(
            CatalogItem(
                item_type='Generic',
                name=new_name,
                description='my catalog',
                display_in=True,
                dialog=dialog.label)
        )

    for catalog_item in catalog_items:
        catalog_item.create()

    collection = rest_api.collections.service_templates

    for new_name in new_names:
        wait_for(lambda: collection.find_by(name=new_name), num_sec=180, delay=10)

    s_tpls = [ent for ent in collection if ent.name in new_names]

    @request.addfinalizer
    def _finished():
        collection.reload()
        to_delete = [ent for ent in collection if ent.name in new_names]
        if len(to_delete) != 0:
            collection.action.delete(*to_delete)

    return s_tpls


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


def _creating_skeleton(request, rest_api, col_name, col_data, col_action='create'):
    collection = getattr(rest_api.collections, col_name)
    try:
        action = getattr(collection.action, col_action)
    except AttributeError:
        raise OptionNotAvailable(
            "Action `{}` for {} is not implemented in this version".format(col_action, col_name))

    entities = action(*col_data)
    action_status = rest_api.response.status_code
    for entity in col_data:
        if entity.get('name', None):
            wait_for(lambda: collection.find_by(name=entity.get('name')), num_sec=180, delay=10)
        elif entity.get('description', None):
            wait_for(lambda: collection.find_by(
                description=entity.get('description')), num_sec=180, delay=10)
        else:
            raise NotImplementedError

    @request.addfinalizer
    def _finished():
        collection.reload()
        ids = [e.id for e in entities]
        delete_entities = [e for e in collection if e.id in ids]
        if len(delete_entities) != 0:
            collection.action.delete(*delete_entities)

    # make sure action status code is preserved
    rest_api.response.status_code = action_status
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
