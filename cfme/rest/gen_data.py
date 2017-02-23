# -*- coding: utf-8 -*-
import fauxfactory

from manageiq_client.api import APIException

from cfme.automate.service_dialogs import ServiceDialog
from cfme.exceptions import OptionNotAvailable
from cfme.infrastructure.provider import InfraProvider
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from utils.providers import setup_a_provider_by_class
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


def service_catalogs(request, rest_api):
    name = fauxfactory.gen_alphanumeric()
    scls_data = [{
        "name": "name_{}_{}".format(name, index),
        "description": "description_{}_{}".format(name, index),
        "service_templates": []
    } for index in range(1, 5)]

    scls = rest_api.collections.service_catalogs.action.add(*scls_data)
    for scl in scls:
        wait_for(
            lambda: rest_api.collections.service_catalogs.find_by(name=scl.name),
            num_sec=180,
            delay=10,
        )

    @request.addfinalizer
    def _finished():
        ids = [s.id for s in scls]
        delete_scls = [s for s in rest_api.collections.service_catalogs if s.id in ids]
        if len(delete_scls) != 0:
            rest_api.collections.service_catalogs.action.delete(*delete_scls)

    return scls


def categories(request, rest_api, num=1):
    ctg_data = [{
        'name': 'test_category_{}_{}'.format(fauxfactory.gen_alphanumeric().lower(), _index),
        'description': 'test_category_{}_{}'.format(fauxfactory.gen_alphanumeric().lower(), _index)
    } for _index in range(0, num)]
    ctgs = rest_api.collections.categories.action.create(*ctg_data)
    for ctg in ctgs:
        wait_for(
            lambda: rest_api.collections.categories.find_by(description=ctg.description),
            num_sec=180,
            delay=10,
        )

    @request.addfinalizer
    def _finished():
        ids = [ctg.id for ctg in ctgs]
        delete_ctgs = [ctg for ctg in rest_api.collections.categories
            if ctg.id in ids]
        if len(delete_ctgs) != 0:
            rest_api.collections.categories.action.delete(*delete_ctgs)

    return ctgs


def tags(request, rest_api, categories):
    # Category id, href or name needs to be specified for creating a new tag resource
    tags = []
    for i, ctg in enumerate(categories):
        refs = [{'id': ctg.id}, {'href': ctg.href}, {'name': ctg.name}]
        data = {
            'name': 'test_tag_{}'.format(fauxfactory.gen_alphanumeric().lower()),
            'description': 'test_tag_{}'.format(fauxfactory.gen_alphanumeric().lower()),
            'category': refs[i % 3]
        }
        tags.append(data)
    tags = rest_api.collections.tags.action.create(*tags)
    for tag in tags:
        wait_for(
            lambda: rest_api.collections.tags.find_by(name=tag.name),
            num_sec=180,
            delay=10,
        )

    @request.addfinalizer
    def _finished():
        ids = [tag.id for tag in tags]
        delete_tags = [tag for tag in rest_api.collections.tags if tag.id in ids]
        if len(delete_tags) != 0:
            rest_api.collections.tags.action.delete(*delete_tags)

    return tags


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
    service_data(request, rest_api, a_provider, dialog, service_catalogs)

    try:
        services = [_ for _ in rest_api.collections.services]
        services[0]
    except IndexError:
        raise Exception("No options are selected")

    @request.addfinalizer
    def _finished():
        services = [_ for _ in rest_api.collections.services]
        if len(services) != 0:
            rest_api.collections.services.action.delete(*services)

    return services


def rates(request, rest_api):
    chargeback = rest_api.collections.chargebacks.get(rate_type='Compute')
    data = [{
        'description': 'test_rate_{}_{}'.format(_index, fauxfactory.gen_alphanumeric()),
        'source': 'allocated',
        'group': 'cpu',
        'per_time': 'daily',
        'per_unit': 'megahertz',
        'chargeback_rate_id': chargeback.id
    } for _index in range(0, 3)]

    rates = rest_api.collections.rates.action.create(*data)
    for rate in data:
        wait_for(
            lambda: rest_api.collections.rates.find_by(description=rate.get('description')),
            num_sec=180,
            delay=10,
        )

    @request.addfinalizer
    def _finished():
        ids = [rate.id for rate in rates]
        delete_rates = [rate for rate in rest_api.collections.rates if rate.id in ids]
        if len(delete_rates) != 0:
            rest_api.collections.rates.action.delete(*delete_rates)

    return rates


def a_provider():
    return setup_a_provider_by_class(InfraProvider)


def vm(request, a_provider, rest_api):
    provider_rest = rest_api.collections.providers.get(name=a_provider.name)
    vm_name = deploy_template(
        a_provider.key,
        "test_rest_vm_{}".format(fauxfactory.gen_alphanumeric(length=4)))

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


def service_templates(request, rest_api, dialog):
    catalog_items = []
    for index in range(1, 5):
        catalog_items.append(
            CatalogItem(
                item_type="Generic",
                name="item_{}_{}".format(index, fauxfactory.gen_alphanumeric()),
                description="my catalog", display_in=True,
                dialog=dialog.label)
        )

    for catalog_item in catalog_items:
        catalog_item.create()

    try:
        s_tpls = [_ for _ in rest_api.collections.service_templates]
        s_tpls[0]
    except IndexError:
        raise Exception("There is no service template to be taken")

    @request.addfinalizer
    def _finished():
        s_tpls = [_ for _ in rest_api.collections.service_templates]
        if len(s_tpls) != 0:
            rest_api.collections.service_templates.action.delete(*s_tpls)

    return s_tpls


def automation_requests_data(vm, requests_collection=False, approve=True):
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
    return [data for _ in range(4)]


def groups(request, rest_api, role, tenant, num=1):
    data = [{
        "description": "group_description_{}".format(fauxfactory.gen_alphanumeric()),
        "role": {"href": role.href},
        "tenant": {"href": tenant.href}
    } for index in range(0, num)]

    groups = _creating_skeleton(request, rest_api, "groups", data)
    if num == 1:
        return groups.pop()
    return groups


def roles(request, rest_api, num=1):
    data = [{
        "name": "role_name_{}".format(fauxfactory.gen_alphanumeric())
    } for index in range(0, num)]

    roles = _creating_skeleton(request, rest_api, "roles", data)
    if num == 1:
        return roles.pop()
    return roles


def tenants(request, rest_api, num=1):
    parent = rest_api.collections.tenants.get(name='My Company')
    data = [{
        'description': 'test_tenants_{}_{}'.format(_index, fauxfactory.gen_alphanumeric()),
        'name': 'test_tenants_{}_{}'.format(_index, fauxfactory.gen_alphanumeric()),
        'divisible': 'true',
        'use_config_for_attributes': 'false',
        'parent': {'href': parent.href}
    } for _index in range(0, num)]

    tenants = _creating_skeleton(request, rest_api, "tenants", data)
    if num == 1:
        return tenants.pop()
    return tenants


def users(request, rest_api, num=1):
    data = [{
        "userid": "user_{}_{}".format(_index, fauxfactory.gen_alphanumeric(3)),
        "name": "name_{}_{}".format(_index, fauxfactory.gen_alphanumeric()),
        "password": "pass_{}_{}".format(_index, fauxfactory.gen_alphanumeric(3)),
        "group": {"description": "EvmGroup-user"}
    } for _index in range(0, num)]

    users = _creating_skeleton(request, rest_api, "users", data)
    if num == 1:
        return users.pop()
    return users


def _creating_skeleton(request, rest_api, col_name, col_data):
    collection = getattr(rest_api.collections, col_name)
    if "create" not in collection.action.all:
        raise OptionNotAvailable(
            "Create action for {} is not implemented in this version".format(col_name))
    entities = collection.action.create(*col_data)
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
    collection = rest_api.collections.arbitration_settings
    body = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(5)
        body.append({
            'name': 'test_settings_{}'.format(uniq),
            'display_name': 'Test Settings {}'.format(uniq)})
    response = collection.action.create(*body)

    @request.addfinalizer
    def _finished():
        try:
            collection.action.delete(*response)
        except APIException:
            # settings can be deleted by tests, just log warning
            logger.warning("Failed to delete arbitration settings.")

    return response


def orchestration_templates(request, rest_api, num=2):
    collection = rest_api.collections.orchestration_templates
    body = []
    for _ in range(num):
        uniq = fauxfactory.gen_alphanumeric(5)
        body.append({
            'name': 'test_{}'.format(uniq),
            'description': 'Test Template {}'.format(uniq),
            'type': 'OrchestrationTemplateCfn',
            'orderable': False,
            'draft': False,
            'content': _TEMPLATE_TORSO.replace('CloudFormation', uniq)})
    response = collection.action.create(*body)

    @request.addfinalizer
    def _finished():
        try:
            collection.action.delete(*response)
        except APIException:
            # settings can be deleted by tests, just log warning
            logger.warning("Failed to delete orchestration templates.")

    return response
