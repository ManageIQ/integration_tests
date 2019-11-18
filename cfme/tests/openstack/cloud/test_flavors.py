"""Tests for Openstack cloud Flavors"""
from random import choice

import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.cloud.instance.openstack import OpenStackInstance
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.generators import random_vm_name
from cfme.utils.rest import assert_response
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([OpenStackProvider], scope='function', required_fields=[
        ['provisioning', 'cloud_tenant'],
        ['provisioning', 'cloud_network']])
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
def private_flavor(appliance, provider):
    prov_data = provider.data['provisioning']
    collection = appliance.collections.cloud_flavors
    private_flavor = collection.create(name=fauxfactory.gen_alpha(12, start="flavor_"),
                               provider=provider,
                               ram=RAM,
                               vcpus=VCPUS,
                               disk=DISK_SIZE,
                               swap=SWAP_SIZE,
                               rxtx=RXTX,
                               is_public=False,
                               tenant=prov_data['cloud_tenant'])

    view = appliance.browser.create_view(navigator.get_class(collection, 'All').VIEW)
    view.flash.assert_success_message(
        'Add of Flavor "{}" was successfully initialized.'.format(private_flavor.name))

    wait_for(lambda: private_flavor.exists, delay=5, timeout=600, fail_func=private_flavor.refresh,
             message='Wait for flavor to appear')

    yield private_flavor

    if private_flavor.exists:
        private_flavor.delete()


@pytest.fixture(scope='function')
def new_instance(provider, zero_disk_flavor):
    flavor_name = zero_disk_flavor.name
    prov_data = provider.data['provisioning']
    prov_form_data = {
        'request': {'email': fauxfactory.gen_email(),
                    'first_name': fauxfactory.gen_alpha(),
                    'last_name': fauxfactory.gen_alpha()},
        'catalog': {'num_vms': '1',
                    'vm_name': random_vm_name("osp")},
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


@pytest.fixture(scope='function')
def instance_with_private_flavor(provider, private_flavor):
    prov_data = provider.data['provisioning']
    flavor_name = private_flavor.name
    prov_form_data = {
        'request': {'email': fauxfactory.gen_email(),
                    'first_name': fauxfactory.gen_alpha(),
                    'last_name': fauxfactory.gen_alpha()},
        'catalog': {'num_vms': '1',
                    'vm_name': random_vm_name("osp")},
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


@pytest.mark.rfe
def test_create_instance_with_zero_disk_flavor(new_instance, soft_assert):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
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


@pytest.mark.regression
def test_flavor_crud(appliance, provider, request):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    collection = appliance.collections.cloud_flavors
    flavor = collection.create(name=fauxfactory.gen_alpha(12, start="flavor_"),
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


@pytest.mark.rfe
def test_flavors_details_from_list_view(appliance, soft_assert, private_flavor):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    collection = appliance.collections.cloud_flavors
    view = navigate_to(collection, 'All')
    item = view.entities.get_entity(name=private_flavor.name, surf_pages=True)
    soft_assert(item.data['name'] == private_flavor.name)
    soft_assert(item.data['cpus'] == str(private_flavor.vcpus))
    soft_assert(item.data['publicly_available'] == str(private_flavor.is_public))
    soft_assert(item.data['memory'].split()[0] == str(private_flavor.ram))
    soft_assert(item.data['cloud_provider'] == private_flavor.provider.name)


@pytest.mark.rfe
def test_flavor_details(appliance, soft_assert, private_flavor):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    view = navigate_to(private_flavor, 'Details')
    soft_assert(view.entities.properties.get_text_of('CPUs') == str(private_flavor.vcpus))

    soft_assert(view.entities.properties.get_text_of('Memory').split()[0] ==
                str(private_flavor.ram))

    soft_assert(view.entities.properties.get_text_of('Public') ==
                str(private_flavor.is_public).lower())

    soft_assert(view.entities.relationships.get_text_of('Cloud Provider') ==
                private_flavor.provider.name)


@pytest.mark.rfe
def test_create_instance_with_private_flavor(instance_with_private_flavor, provider, soft_assert):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    view = navigate_to(instance_with_private_flavor, 'Details')
    prov_data = provider.data['provisioning']
    power_state = view.entities.summary('Power Management').get_text_of('Power State')
    assert power_state == OpenStackInstance.STATE_ON

    vm_tmplt = view.entities.summary('Relationships').get_text_of('VM Template')
    soft_assert(vm_tmplt == prov_data['image']['name'])

    flavor = view.entities.summary('Relationships').get_text_of('Flavor')
    flavors = [flv.name for flv in provider.appliance.collections.cloud_flavors.all()]
    soft_assert(flavor in flavors)

    props = {"Availability Zone": "availability_zone",
             "Cloud Tenants": "cloud_tenant",
             "Virtual Private Cloud": "cloud_network"}

    view = navigate_to(instance_with_private_flavor, 'Details')
    for key, val in props.items():
        v = view.entities.summary('Relationships').get_text_of(key)
        soft_assert(v == prov_data[val])

    collection = provider.appliance.collections.cloud_flavors
    flavor_obj = collection.instantiate(flavor, provider)
    assert flavor_obj.instance_count == 1

    flavor_obj.delete()
    view = navigate_to(collection, "All")
    view.flash.assert_success_message(
        'Delete of Flavor "{name}" was successfully initiated.'.format(name=flavor_obj.name))

    wait_for(lambda: not flavor_obj.exists, delay=5, timeout=600, fail_func=flavor_obj.refresh,
             message='Wait for flavor to disappear')

    view = navigate_to(instance_with_private_flavor, 'Details')
    power_state = view.entities.summary('Power Management').get_text_of('Power State')
    assert power_state == OpenStackInstance.STATE_ON


@test_requirements.rest
@pytest.mark.tier(3)
def test_filter_by_flavor_via_api(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/10h
        setup:
            1.Add a cloud provider.
        testSteps:
            1. Send a GET request: /api/vms?filter[]=flavor.name="<flavor_name>"
        expectedResults:
            1. Should receive a 200 OK response. Should not get any internal server error.

    Bugzilla:
        1596069
    """
    flavor = choice(appliance.rest_api.collections.flavors.all)
    url = "/api/vms?filter[]=flavor.name='{}'".format(flavor.name)
    appliance.rest_api.get(appliance.url_path(url))
    assert_response(appliance)
