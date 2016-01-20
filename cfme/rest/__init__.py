import fauxfactory
import pytest

from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
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


def tenants(request, rest_api, num=1):
    parent = rest_api.collections.tenants.get(name='My Company')
    data = [{
        'description': 'test_tenants_{}_{}'.format(_index, fauxfactory.gen_alphanumeric()),
        'name': 'test_tenants_{}_{}'.format(_index, fauxfactory.gen_alphanumeric()),
        'divisible': 'true',
        'use_config_for_attributes': 'false',
        'parent': {'href': parent.href}
    } for _index in range(0, num)]

    tenants = rest_api.collections.tenants.action.create(*data)
    for tenant in data:
        wait_for(
            lambda: rest_api.collections.tenants.find_by(name=tenant.get('name')),
            num_sec=180,
            delay=10,
        )

    @request.addfinalizer
    def _finished():
        ids = [tenant.id for tenant in tenants]
        delete_tenants = [tenant for tenant in rest_api.collections.tenants if tenant.id in ids]
        if len(delete_tenants) != 0:
            rest_api.collections.tenants.action.delete(*delete_tenants)

    return tenants


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
        pytest.skip("There is no service to be taken")

    @request.addfinalizer
    def _finished():
        services = [_ for _ in rest_api.collections.services]
        if len(services) != 0:
            rest_api.collections.services.action.delete(*services)

    return services


def roles(request, rest_api):
    if "create" not in rest_api.collections.roles.action.all:
        pytest.skip("Create roles action is not implemented in this version")

    roles_data = [{
        "name": "role_name_{}".format(fauxfactory.gen_alphanumeric())
    } for index in range(1, 5)]

    roles = rest_api.collections.roles.action.create(*roles_data)
    for role in roles:
        wait_for(
            lambda: rest_api.collections.roles.find_by(name=role.name),
            num_sec=180,
            delay=10,
        )

    @request.addfinalizer
    def _finished():
        ids = [r.id for r in roles]
        delete_roles = [r for r in rest_api.collections.roles if r.id in ids]
        if len(delete_roles) != 0:
            rest_api.collections.roles.action.delete(*delete_roles)

    return roles


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
