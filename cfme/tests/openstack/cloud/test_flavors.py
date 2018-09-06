"""Tests for Openstack cloud Flavors"""

import fauxfactory
import pytest

from cfme.cloud.instance.openstack import OpenStackInstance
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigator, navigate_to
from cfme.utils.wait import wait_for
from widgetastic.utils import partial_match

pytestmark = [
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([OpenStackProvider], scope='function')
]


DISK_SIZE = 1
RAM = 64
VCPUS = 1
SWAP_SIZE = 1
RXTX = 1
ZERO_DISK_SIZE = 0


@pytest.fixture(scope='function')
def zero_disk_flavor(provider):
    api_flv = provider.mgmt.api.flavors.create(fauxfactory.gen_alpha(), RAM, VCPUS, ZERO_DISK_SIZE)
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    zero_disk_flavor = provider.appliance.collections.cloud_flavors.instantiate(
        api_flv.name, provider)

    yield zero_disk_flavor

    if zero_disk_flavor.exists:
        zero_disk_flavor.delete()


@pytest.fixture(scope='function')
def new_instance(provider, zero_disk_flavor):
    flavor_name = zero_disk_flavor.name
    prov_data = provider.data['provisioning']
    prov_form_data = {
        'request': {'email': fauxfactory.gen_email(),
                    'first_name': fauxfactory.gen_alpha(),
                    'last_name': fauxfactory.gen_alpha()},
        'catalog': {'num_vms': '1',
                    'vm_name': fauxfactory.gen_alpha()},
        'environment': {'cloud_network': prov_data['cloud_network'],
                        'cloud_tenant': prov_data['cloud_tenant']},
        'properties': {'instance_type': partial_match(flavor_name)},
    }

    instance_name = prov_form_data['catalog']['vm_name']

    try:
        instance = provider.appliance.collections.cloud_instances.create(
            instance_name,
            provider,
            prov_form_data, find_in_cfme=True
        )

    except KeyError:
        # some yaml value wasn't found
        pytest.skip('Unable to find an image map in provider "{}" provisioning data: {}'
                    .format(provider, prov_data))

    yield instance

    instance.cleanup_on_provider()


@pytest.mark.ignore_stream('5.9')
def test_create_instance_with_zero_disk_flavor(new_instance, soft_assert):
    view = navigate_to(new_instance, 'Details')
    prov_data = new_instance.provider.data['provisioning']
    power_state = view.entities.summary('Power Management').get_text_of('Power State')
    assert power_state == OpenStackInstance.STATE_ON

    vm_tmplt = view.entities.summary('Relationships').get_text_of('VM Template')
    soft_assert(vm_tmplt == prov_data['image']['name'])

    flavors = [f.name for f in new_instance.provider.mgmt.api.flavors.list()]
    flavor = view.entities.summary('Relationships').get_text_of('Flavor')
    soft_assert(flavor in flavors)

    # Assert other relationships in a loop
    props = [('Availability Zone', 'availability_zone'),
             ('Cloud Tenants', 'cloud_tenant'),
             ('Virtual Private Cloud', 'cloud_network')]

    for p in props:
        v = view.entities.summary('Relationships').get_text_of(p[0])
        soft_assert(v == prov_data[p[1]])


def test_flavor_crud(appliance, provider, request):
    collection = appliance.collections.cloud_flavors
    flavor = collection.create(name=fauxfactory.gen_alpha(),
                               provider=provider,
                               ram=RAM,
                               vcpus=VCPUS,
                               disk=DISK_SIZE,
                               swap=SWAP_SIZE,
                               rxtx=RXTX)

    @request.addfinalizer
    def cleanup():
        if flavor.exists:
            flavor.delete()

    view = appliance.browser.create_view(navigator.get_class(collection, 'All').VIEW)
    view.flash.assert_success_message(
        'Add of Flavor "{}" was successfully initialized.'.format(flavor.name))

    wait_for(lambda: flavor.exists, delay=5, timeout=600, fail_func=flavor.refresh,
             message='Wait for flavor to appear')

    flavor.delete()
    view = appliance.browser.create_view(navigator.get_class(collection, 'All').VIEW)
    view.flash.assert_success_message(
        'Delete of Flavor "{}" was successfully initiated.'.format(flavor.name))

    wait_for(lambda: not flavor.exists, delay=5, timeout=600, fail_func=flavor.refresh,
             message='Wait for flavor to appear')
