import fauxfactory

from cfme.automate.service_dialogs import ServiceDialog
from cfme.exceptions import OptionNotAvailable
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from utils.providers import setup_a_provider as _setup_a_provider
from utils.virtual_machines import deploy_template
from utils.wait import wait_for
from utils import version


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
    for ctg in categories:
        data = {
            'name': 'test_tag_{}'.format(fauxfactory.gen_alphanumeric().lower()),
            'description': 'test_tag_{}'.format(fauxfactory.gen_alphanumeric().lower()),
            'category': {'href': ctg.href}
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


def services(request, rest_api, a_provider, dialog, service_catalogs):
    """
    The attempt to add the service entities via web
    """
    template, host, datastore, iso_file, vlan, catalog_item_type = map(a_provider.data.get(
        "provisioning").get,
        ('template', 'host', 'datastore', 'iso_file', 'vlan', 'catalog_item_type'))

    provisioning_data = {
        'vm_name': 'test_rest_{}'.format(fauxfactory.gen_alphanumeric()),
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]}
    }

    if a_provider.type == 'rhevm':
        provisioning_data['provision_type'] = 'Native Clone'
        provisioning_data['vlan'] = vlan
        catalog_item_type = version.pick({
            version.LATEST: "RHEV",
            '5.3': "RHEV",
            '5.2': "Redhat"
        })
    elif a_provider.type == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'
    catalog = service_catalogs[0].name
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
        'rate': 1,
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
