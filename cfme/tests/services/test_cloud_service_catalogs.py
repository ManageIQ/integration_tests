import fauxfactory
import pytest
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytestmark = [
    test_requirements.service,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.tier(2),
    pytest.mark.provider([CloudProvider], selector=ONE_PER_TYPE,
                         required_fields=[['provisioning', 'image']],
                         scope="module"),
]


@pytest.fixture()
def vm_name():
    return random_vm_name(context='provs')


@pytest.mark.meta(blockers=[BZ(1626232, forced_streams=['5.10'])])
def test_cloud_catalog_item(appliance, vm_name, setup_provider, provider, dialog, catalog, request,
                            provisioning):
    """Tests cloud catalog item

    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
    """
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    vm = appliance.collections.cloud_instances.instantiate("{}0001".format(vm_name), provider)

    request.addfinalizer(lambda: vm.cleanup_on_provider())
    image = provisioning['image']['name']
    item_name = "{}-service-{}".format(provider.name, fauxfactory.gen_alphanumeric())

    inst_args = {
        'catalog': {'catalog_name': {'name': image, 'provider': provider.name},
                    'vm_name': vm_name},
        'environment': {
            'availability_zone': provisioning.get('availability_zone', None),
            'security_groups': [provisioning.get('security_group', None)],
            'cloud_tenant': provisioning.get('cloud_tenant', None),
            'cloud_network': provisioning.get('cloud_network', None),
            'cloud_subnet': provisioning.get('cloud_subnet', None),
            'resource_groups': provisioning.get('resource_group', None)
        },
        'properties': {
            'instance_type': partial_match(provisioning.get('instance_type', None)),
            'guest_keypair': provisioning.get('guest_keypair', None)}
    }
    # GCE specific
    if provider.one_of(GCEProvider):
        recursive_update(inst_args, {
            'properties': {
                'boot_disk_size': provisioning['boot_disk_size'],
                'is_preemptible': True}
        })
    # Azure specific
    if provider.one_of(AzureProvider):
        recursive_update(inst_args, {
            'customize': {
                'admin_username': provisioning['customize_username'],
                'root_password': provisioning['customize_password']}})

    catalog_item = appliance.collections.catalog_items.create(
        provider.catalog_item_type,
        name=item_name,
        description="my catalog",
        display_in=True,
        catalog=catalog,
        dialog=dialog,
        prov_data=inst_args
    )
    request.addfinalizer(catalog_item.delete)
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', item_name)
    request_description = item_name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = "Request failed with the message {}".format(provision_request.rest.message)
    assert provision_request.is_succeeded(), msg
