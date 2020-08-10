import fauxfactory
import pytest
import yaml
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme.automate.dialog_import_export import DialogImportExport
from cfme.base.credential import Credential
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.templates import _get_template
from cfme.infrastructure.provider import InfraProvider
from cfme.rest.gen_data import dialog as _dialog
from cfme.rest.gen_data import service_catalog_obj as _catalog
from cfme.rest.gen_data import service_templates_rest as _service_templates
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaUI
from cfme.utils.conf import cfme_data
from cfme.utils.ftp import FTPClientWrapper
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger


@pytest.fixture(scope="function")
def dialog(request, appliance):
    return _dialog(request, appliance)


@pytest.fixture(scope="module")
def dialog_modscope(request, appliance):
    return _dialog(request, appliance)


@pytest.fixture(scope="function")
def catalog(request, appliance):
    return _catalog(request, appliance)


@pytest.fixture(scope="module")
def catalog_modscope(request, appliance):
    return _catalog(request, appliance)


@pytest.fixture(scope="function")
def catalog_item(appliance, provider, provisioning, dialog, catalog, request):
    catalog_item = create_catalog_item(appliance, provider, provisioning, dialog, catalog)
    request.addfinalizer(catalog_item.delete_if_exists)
    return catalog_item


@pytest.fixture(scope="module")
def catalog_item_modscope(appliance, provider, provisioning, dialog_modscope, catalog_modscope):
    catalog_item = create_catalog_item(
        appliance, provider, provisioning, dialog_modscope, catalog_modscope
    )
    return catalog_item


@pytest.fixture(scope="module")
def generic_catalog_item(request, appliance, dialog_modscope, catalog_modscope):
    cat = _service_templates(
        request, appliance, service_dialog=dialog_modscope, service_catalog=catalog_modscope, num=1
    )[0]

    yield appliance.collections.catalog_items.instantiate(
        appliance.collections.catalog_items.GENERIC,
        name=cat.name,
        description=cat.description,
        display_in=True,
        catalog=catalog_modscope,
        dialog=dialog_modscope,
    )

    if cat.exists:
        cat.action.delete()


def create_catalog_item(appliance, provider, provisioning, dialog, catalog,
         vm_count='1', console_test=False):
    provision_type, template, host, datastore, iso_file, vlan = map(provisioning.get,
        ('provision_type', 'template', 'host', 'datastore', 'iso_file', 'vlan'))
    if console_test:
        template = _get_template(provider, 'console_template').name
        logger.info(f"Console template name : {template}")
    item_name = dialog.label
    if provider.one_of(InfraProvider):
        catalog_name = template
        provisioning_data = {
            'catalog': {'catalog_name': {'name': catalog_name, 'provider': provider.name},
                        'vm_name': random_vm_name('serv'),
                        'provision_type': provision_type,
                        'num_vms': vm_count},
            'environment': {'host_name': {'name': host},
                            'datastore_name': {'name': datastore}},
            'network': {'vlan': partial_match(vlan)},
        }
    elif provider.one_of(CloudProvider):
        catalog_name = provisioning['image']['name']
        provisioning_data = {
            'catalog': {'catalog_name': {'name': catalog_name, 'provider': provider.name},
                        'vm_name': random_vm_name('serv')},
            'properties': {'instance_type': partial_match(provisioning.get('instance_type', None)),
                           'guest_keypair': provisioning.get('guest_keypair', None)},
        }
        # Azure specific
        if provider.one_of(AzureProvider):
            recursive_update(provisioning_data, {
                'customize': {
                    'admin_username': provisioning['customize_username'],
                    'root_password': provisioning['customize_password']},
                'environment': {
                    'security_groups': provisioning['security_group'],
                    'cloud_network': provisioning['cloud_network'],
                    'cloud_subnet': provisioning['cloud_subnet'],
                    'resource_groups': provisioning['resource_group']},

            })
        # GCE specific
        if provider.one_of(GCEProvider):
            recursive_update(provisioning_data, {
                'properties': {
                    'boot_disk_size': provisioning['boot_disk_size'],
                    'is_preemptible': True},
                'environment': {
                    'availability_zone': provisioning['availability_zone'],
                    'cloud_network': provisioning['cloud_network']},
            })
        # EC2 specific
        if provider.one_of(EC2Provider):
            recursive_update(provisioning_data, {
                'environment': {
                    'availability_zone': provisioning['availability_zone'],
                    'cloud_network': provisioning['cloud_network'],
                    'cloud_subnet': provisioning['cloud_subnet'],
                    'security_groups': provisioning['security_group'],
                },
            })
            # OpenStack specific
        if provider.one_of(OpenStackProvider):
            recursive_update(provisioning_data, {
                'environment': {
                    'availability_zone': provisioning['availability_zone'],
                    'cloud_network': provisioning['cloud_network'],
                    'cloud_tenant': provisioning['cloud_tenant'],
                    'security_groups': provisioning['security_group'],
                },
            })

    catalog_item = appliance.collections.catalog_items.create(
        provider.catalog_item_type, name=item_name,
        description="my catalog", display_in=True, catalog=catalog,
        dialog=dialog, prov_data=provisioning_data, provider=provider
    )
    return catalog_item


@pytest.fixture
def order_service(appliance, provider, provisioning, dialog, catalog, request):
    # BZ 1646333 - Delete this request button is not shown in service Request details page
    # The above BZ got closed because of  INSUFFICIENT_DATA, so I havve reported the same issue
    # in BZ 775779.
    """ Orders service once the catalog item is created"""
    param = getattr(request, 'param', None)
    vm_count = '1'
    console_test = False
    if isinstance(param, dict):
        vm_count = param.get('vm_count', vm_count)
        console_test = param.get('console_test', console_test)
    catalog_item = create_catalog_item(appliance, provider, provisioning, dialog, catalog,
                                       vm_count=vm_count, console_test=console_test)
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    provision_request = service_catalogs.order()
    provision_request.wait_for_request(method='ui')
    assert provision_request.is_succeeded()
    if provision_request.exists():
        provision_request.wait_for_request()
        # Provision request is being removed through REST API because of BZ 775779.
        provision_request.remove_request(method='rest')
    yield catalog_item
    service = MyService(appliance, catalog_item.name)
    if service.exists:
        service.delete()
    name = catalog_item.prov_data['catalog']['vm_name']
    for i in range(int(vm_count)):
        vm_name = f'{name}000{i+1}'
        vm = appliance.collections.infra_vms.instantiate(vm_name, provider)
        vm.cleanup_on_provider()


@pytest.fixture()
def service_vm(appliance, provider, catalog_item):
    """ This is global fixture to get service and vm/instance provision by service."""

    collection = provider.appliance.provider_based_collection(provider)
    vm_name = "{}0001".format(catalog_item.prov_data["catalog"]["vm_name"])
    vm = collection.instantiate(f"{vm_name}", provider)

    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    provision_request = service_catalogs.order()
    logger.info("Waiting for service provision request for service %s", catalog_item.name)
    provision_request.wait_for_request()

    if not provision_request.is_finished():
        pytest.skip(f"Failed to provision service '{catalog_item.name}'")

    service = MyService(appliance, catalog_item.name, vm_name=vm_name)
    yield service, vm

    vm.cleanup_on_provider()
    if service.exists:
        service.delete()
    if provision_request.exists:
        provision_request.remove_request(method="rest")


@pytest.fixture(scope="module")
def generic_service(appliance, generic_catalog_item):
    """ This is global fixture to order generic service and return service and catalog item"""

    service_catalogs = ServiceCatalogs(
        appliance, catalog=generic_catalog_item.catalog, name=generic_catalog_item.name
    )
    provision_request = service_catalogs.order()
    logger.info("Waiting for service provision request for service %s", generic_catalog_item.name)
    provision_request.wait_for_request()

    if not provision_request.is_finished():
        pytest.skip(f"Failed to provision service '{generic_catalog_item.name}'")

    service = MyService(appliance, generic_catalog_item.dialog.label)
    yield service, generic_catalog_item
    if service.exists:
        service.delete()
    if provision_request.exists:
        provision_request.remove_request(method="rest")


@pytest.fixture()
def import_dialog(appliance, file_name):
    """This fixture will help to import dialog file."""

    # Download dialog file from FTP server
    fs = FTPClientWrapper(cfme_data.ftpserver.entities.dialogs)
    file_path = fs.download(file_name)

    # Import dialog yml to appliance
    import_export = DialogImportExport(appliance)
    import_export.import_dialog(file_path)

    # Read yml to get the field name
    with open(file_path) as stream:
        dialog = yaml.load(stream, Loader=yaml.BaseLoader)
        # It returns list of dicts
        description = dialog[0].get("description")
        label = dialog[0].get("label")
        ele_label = dialog[0]['dialog_tabs'][0]['dialog_groups'][0]['dialog_fields'][0]['name']

    # File name contains '.yml' or '.yaml', Hence replacing it.
    sd = appliance.collections.service_dialogs.instantiate(label=label, description=description)
    yield sd, ele_label
    sd.delete_if_exists()


@pytest.fixture(scope="function")
def catalog_item_with_imported_dialog(appliance, provider, provisioning, import_dialog, catalog):
    """Catalog Item with imported dialog"""
    catalog_item = create_catalog_item(appliance, provider, provisioning, import_dialog[0], catalog)
    yield catalog_item, import_dialog[1]
    catalog_item.delete_if_exists()
    catalog.delete_if_exists()


@pytest.fixture(scope="module")
def user_self_service_role(appliance):
    """This is fixture with create user with user_self_service_role"""

    with appliance.context.use(ViaUI):
        # copy role with no restrictions
        role = appliance.collections.roles.instantiate(name="EvmRole-user_self_service")
        user_self_service_role = role.copy(
            name=fauxfactory.gen_alphanumeric(25, "self_service_role_"),
            vm_restriction="None"
        )

        # Group with user self service role
        user_self_service_gp = appliance.collections.groups.create(
            description=fauxfactory.gen_alphanumeric(22, "self_service_gp_"),
            role=user_self_service_role.name
        )

        # credentials for user
        creds = Credential(
            principal=fauxfactory.gen_alphanumeric(start="user_"),
            secret=fauxfactory.gen_alphanumeric(),
        )

        # user with above group
        user = appliance.collections.users.create(
            name=fauxfactory.gen_alphanumeric(start="user_"),
            credential=creds,
            email=fauxfactory.gen_email(),
            groups=user_self_service_gp,
        )

        yield user, user_self_service_role
        user.delete_if_exists()
        user_self_service_gp.delete_if_exists()
        user_self_service_role.delete_if_exists()


@pytest.fixture()
def generic_catalog_item_with_imported_dialog(request, appliance, import_dialog, catalog):
    sd, ele_label = import_dialog
    cat = _service_templates(
        request, appliance, service_dialog=sd, service_catalog=catalog, num=1
    )[0]

    catalog_item = appliance.collections.catalog_items.instantiate(
        appliance.collections.catalog_items.GENERIC,
        name=cat.name,
        description=cat.description,
        display_in=True,
        catalog=catalog,
        dialog=sd,
    )
    yield catalog_item, sd, ele_label
    if cat.exists:
        cat.action.delete()
