# -*- coding: utf-8 -*-
import fauxfactory

from cfme.automate.service_dialogs import ServiceDialog
from cfme.exceptions import OptionNotAvailable
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from utils.providers import setup_a_provider as _setup_a_provider
from utils.virtual_machines import deploy_template
from utils.wait import wait_for


def service_catalogs(request, rest_api, num=1):
    name = fauxfactory.gen_alphanumeric()
    scls_data = [{
        "name": "name_{}_{}".format(name, index),
        "description": "description_{}_{}".format(name, index),
        "service_templates": []
    } for index in range(0, num)]

    scls = _creating_skeleton(request, rest_api, "service_catalogs", scls_data)
    if num == 1:
        return scls.pop()
    return scls


def categories(request, rest_api, num=1):
    ctgs_data = [{
        'name': 'test_category_{}_{}'.format(fauxfactory.gen_alphanumeric().lower(), _index),
        'description': 'test_category_{}_{}'.format(fauxfactory.gen_alphanumeric().lower(), _index)
    } for _index in range(0, num)]
    ctgs = _creating_skeleton(request, rest_api, "categories", ctgs_data)
    if num == 1:
        return ctgs.pop()
    return ctgs


def tags(request, rest_api, categories):
    # Category id, href or name needs to be specified for creating a new tag resource
    tags_data = []
    for ctg in categories:
        data = {
            'name': 'test_tag_{}'.format(fauxfactory.gen_alphanumeric().lower()),
            'description': 'test_tag_{}'.format(fauxfactory.gen_alphanumeric().lower()),
            'category': {'href': ctg.href}
        }
        tags_data.append(data)
    tags = _creating_skeleton(request, rest_api, "tags", tags_data)
    if len(categories) == 1:
        return tags.pop()
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


def services(request, rest_api, a_provider, dialog, service_catalog, num=1):
    """
    The attempt to add the services entities via web
    """
    template, host, datastore, iso_file, vlan, catalog_item_type = map(a_provider.data.get(
        "provisioning").get,
        ('template', 'host', 'datastore', 'iso_file', 'vlan', 'catalog_item_type'))

    provisioning_data = {
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
        'vlan': vlan
    }

    if a_provider.type == 'rhevm':
        provisioning_data['provision_type'] = 'Native Clone'
    elif a_provider.type == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'

    catalog = service_catalog.name
    service_names = []
    for i in range(0, num):
        provisioning_data['vm_name'] = 'test_rest_{}_{}'.format(fauxfactory.gen_alphanumeric(), i),
        item_name = fauxfactory.gen_alphanumeric()
        catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
                                   description="my catalog", display_in=True,
                                   catalog=catalog,
                                   dialog=dialog.label,
                                   catalog_name=template,
                                   provider=a_provider.name,
                                   prov_data=provisioning_data)

        catalog_item.create()
        service_catalogs = ServiceCatalogs("service_name")
        service_catalogs.order(catalog_item.catalog, catalog_item)
        row_description = catalog_item.name
        cells = {'Description': row_description}
        row, __ = wait_for(requests.wait_for_request, [cells, True],
            fail_func=requests.reload, num_sec=2000, delay=20)
        assert row.last_message.text == 'Request complete'
        service_names.append(catalog_item.name)

    services = [_ for _ in rest_api.collections.services if _.name in service_names]

    @request.addfinalizer
    def _finished():
        ids = [e.id for e in services]
        delete_services = [e for e in rest_api.collections.services if e.id in ids]
        if len(delete_services) != 0:
            rest_api.collections.services.action.delete(*delete_services)

    return services


def rates(request, rest_api, num=1):
    chargeback = rest_api.collections.chargebacks.get(rate_type='Compute')
    data = [{
        'description': 'test_rate_{}_{}'.format(_index, fauxfactory.gen_alphanumeric()),
        'rate': 1,
        'group': 'cpu',
        'per_time': 'daily',
        'per_unit': 'megahertz',
        'chargeback_rate_id': chargeback.id
    } for _index in range(0, num)]

    rates = _creating_skeleton(request, rest_api, "rates", data)
    if num == 1:
        return rates.pop()
    return rates


def a_provider():
    return _setup_a_provider("infra")


def vm(request, a_provider, rest_api):
    provider_rest = rest_api.collections.providers.get(name=a_provider.name)
    vm_name = deploy_template(
        a_provider.key,
        "test_rest_vm_{}".format(fauxfactory.gen_alphanumeric(length=4)))
    request.addfinalizer(lambda: a_provider.mgmt.delete_vm(vm_name))
    provider_rest.action.refresh()
    wait_for(
        lambda: len(rest_api.collections.vms.find_by(name=vm_name)) > 0,
        num_sec=600, delay=5)
    return vm_name


def service_templates(request, rest_api, dialog, service_catalog, num=1):
    catalog_items = []
    for index in range(0, num):
        catalog_items.append(
            CatalogItem(
                item_type="Generic",
                name="item_{}_{}".format(index, fauxfactory.gen_alphanumeric()),
                description="my catalog", display_in=True,
                catalog=service_catalog.name,
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


def automation_requests_data(vm):
    return [{
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
            "auto_approve": True
        }
    } for index in range(1, 5)]


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
    provider.mgmt.wait_vm_stopped(vm_name=vm_name, num_sec=600)

    provider.mgmt.mark_as_template(vm_name, delete=False)

    wait_for(
        lambda: rest_api.collections.templates.find_by(name=vm_name).subcount != 0,
        num_sec=700, delay=15)
    return rest_api.collections.templates.get(name=vm_name)
