# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.services.catalogs import cloud_catalog_item as cct
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from cfme.web_ui import flash
from utils import testgen
from utils.log import logger
from utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures("logged_in"),
    pytest.mark.meta(server_roles="+automate"),
]


def pytest_generate_tests(metafunc):
    # Filter out providers without templates defined
    argnames, argvalues, idlist = testgen.cloud_providers(metafunc, 'provisioning')
    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # Don't know what type of instance to provision, move on
            continue

        # required keys should be a subset of the dict keys set
        if not {'image'}.issubset(args['provisioning'].viewkeys()):
            # Need image for image -> instance provisioning
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append([args[argname] for argname in argnames])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.yield_fixture(scope="function")
def dialog():
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data = dict(
        ele_label="ele_" + fauxfactory.gen_alphanumeric(),
        ele_name=fauxfactory.gen_alphanumeric(),
        ele_desc="my ele desc",
        choose_type="Text Box",
        default_text_box="default value"
    )
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                                   submit=True, cancel=True,
                                   tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                                   tab_desc="my tab desc",
                                   box_label="box_" + fauxfactory.gen_alphanumeric(),
                                   box_desc="my box desc")
    service_dialog.create(element_data)
    flash.assert_success_message('Dialog "{}" was added'.format(dialog))
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    cat_name = "cat_" + fauxfactory.gen_alphanumeric()
    catalog = Catalog(name=cat_name, description="my catalog")
    catalog.create()
    yield catalog


@pytest.mark.meta(blockers=1290932)
def test_cloud_catalog_item(setup_provider, provider, provisioning, dialog, catalog, request):
    """Tests cloud catalog item

    Metadata:
        test_flag: provision
    """

    vm_name = 'test_servicecatalog-{}'.format(fauxfactory.gen_alphanumeric())
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    image = provisioning['image']['name']
    item_name = fauxfactory.gen_alphanumeric()

    cloud_catalog_item = cct.Instance(
        item_type=provisioning['item_type'],
        name=item_name,
        description="my catalog",
        display_in=True,
        catalog=catalog.name,
        dialog=dialog,
        catalog_name=image,
        vm_name=vm_name,
        instance_type=provisioning['instance_type'],
        availability_zone=provisioning['availability_zone'],
        cloud_tenant=provisioning['cloud_tenant'],
        cloud_network=provisioning['cloud_network'],
        security_groups=[provisioning['security_group']],
        provider_mgmt=provider.mgmt,
        provider=provider.name,
        guest_keypair=provisioning['guest_keypair'])

    cloud_catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog.name, cloud_catalog_item)
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s', item_name)
    row_description = item_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=1000, delay=20)
    assert row.last_message.text == 'Request complete'
