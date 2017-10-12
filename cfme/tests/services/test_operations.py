# -*- coding: utf-8 -*-
"""Tests checking for link access from outside."""
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import Vm
from cfme.fixtures import pytest_selenium as sel
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.browser import browser
from cfme.utils.wait import wait_for
from fixtures.provider import setup_one_by_class_or_skip
from fixtures.pytest_store import store


pytestmark = [
    pytest.mark.meta(server_roles="-automate"),  # To prevent the provisioning itself.
    test_requirements.service
]


@pytest.fixture(scope='module')
def a_provider(request):
    return setup_one_by_class_or_skip(request, InfraProvider)


@pytest.fixture(scope="module")
def provider_data(a_provider):
    return a_provider.get_yaml_data()


@pytest.fixture(scope="module")
def provisioning(provider_data):
    return provider_data.get("provisioning", {})


@pytest.fixture(scope="module")
def template_name(provisioning):
    return provisioning.get("template")


@pytest.fixture(scope="module")
def vm_name():
    return fauxfactory.gen_alphanumeric(length=16)


@pytest.yield_fixture(scope="module")
def generated_request(appliance,
                      a_provider, provider_data, provisioning, template_name, vm_name):
    """Creates a provision request, that is not automatically approved, and returns the search data.

    After finishing the test, request should be automatically deleted.

    Slightly modified code from :py:module:`cfme.tests.infrastructure.test_provisioning`
    """
    first_name = fauxfactory.gen_alphanumeric()
    last_name = fauxfactory.gen_alphanumeric()
    notes = fauxfactory.gen_alphanumeric()
    e_mail = "{}@{}.test".format(first_name, last_name)
    host, datastore = map(provisioning.get, ('host', 'datastore'))
    vm = Vm(name=vm_name, provider=a_provider, template_name=template_name)
    view = navigate_to(vm, 'Provision')

    provisioning_data = {
        'request': {
            'email': e_mail,
            'first_name': first_name,
            'last_name': last_name,
            'notes': notes},
        'catalog': {
            'vm_name': vm_name,
            'num_vms': '10'},
        'environment':
            {'host_name': {'name': host},
             'datastore_name': {'name': datastore}},
    }

    # Same thing, different names. :\
    if provider_data["type"] == 'rhevm':
        provisioning_data['catalog']['provision_type'] = 'Native Clone'
    elif provider_data["type"] == 'virtualcenter':
        provisioning_data['catalog']['provision_type'] = 'VMware'

    try:
        provisioning_data['network'] = {'vlan': provisioning['vlan']}
    except KeyError:
        # provisioning['vlan'] is required for rhevm provisioning
        if provider_data["type"] == 'rhevm':
            raise pytest.fail('rhevm requires a vlan value in provisioning info')

    view.form.fill_with(provisioning_data, on_change=view.form.submit_button)
    request_cells = {
        "Description": "Provision from [{}] to [{}###]".format(template_name, vm_name),
    }
    provision_request = appliance.collections.requests.instantiate(cells=request_cells)
    yield provision_request

    browser().get(store.base_url)
    appliance.server.login_admin()

    provision_request.remove_request()


@pytest.mark.tier(3)
def test_services_request_direct_url(generated_request):
    """Go to the request page, save the url and try to access it directly."""

    assert navigate_to(generated_request, 'Details'), "could not find the request!"
    request_url = sel.current_url()
    sel.get(sel.base_url())    # I need to flip it with something different here
    sel.get(request_url)        # Ok, direct access now.
    wait_for(
        lambda: sel.is_displayed("//body[contains(@onload, 'miqOnLoad')]"),
        num_sec=20,
        message="wait for a CFME page appear",
        delay=0.5
    )


@pytest.mark.tier(3)
def test_copy_request(request, generated_request, vm_name, template_name):
    """Check if request gets properly copied."""
    modifications = {'catalog': {'vm_name': fauxfactory.gen_alphanumeric(length=16)}}
    new_request = generated_request.copy_request(values=modifications)
    request.addfinalizer(new_request.remove_request)
    assert navigate_to(new_request, 'Details')
