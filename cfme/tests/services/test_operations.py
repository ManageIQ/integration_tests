# -*- coding: utf-8 -*-
"""Tests checking for link access from outside."""
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.virtual_machines import Vm
from cfme.fixtures import pytest_selenium as sel
from cfme.provisioning import provisioning_form
from cfme.services.requests import RequestCollection
from cfme.web_ui import flash, fill
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.browser import browser
from cfme.utils.wait import wait_for
from fixtures.pytest_store import store


pytestmark = [
    pytest.mark.meta(server_roles="-automate"),  # To prevent the provisioning itself.
    test_requirements.service
]


@pytest.fixture(scope="module")
def provider_data(infra_provider):
    return infra_provider.get_yaml_data()


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
                      infra_provider, provider_data, provisioning, template_name, vm_name):
    """Creates a provision request, that is not automatically approved, and returns the search data.

    After finishing the test, request should be automatically deleted.

    Slightly modified code from :py:module:`cfme.tests.infrastructure.test_provisioning`
    """
    first_name = fauxfactory.gen_alphanumeric()
    last_name = fauxfactory.gen_alphanumeric()
    notes = fauxfactory.gen_alphanumeric()
    e_mail = "{}@{}.test".format(first_name, last_name)
    host, datastore = map(provisioning.get, ('host', 'datastore'))
    vm = Vm(name=vm_name, provider=infra_provider, template_name=template_name)
    navigate_to(vm, 'Provision')

    provisioning_data = {
        'email': e_mail,
        'first_name': first_name,
        'last_name': last_name,
        'notes': notes,
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
        'num_vms': "10",    # so it won't get auto-approved
    }

    # Same thing, different names. :\
    if provider_data["type"] == 'rhevm':
        provisioning_data['provision_type'] = 'Native Clone'
    elif provider_data["type"] == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'

    try:
        provisioning_data['vlan'] = provisioning['vlan']
    except KeyError:
        # provisioning['vlan'] is required for rhevm provisioning
        if provider_data["type"] == 'rhevm':
            raise pytest.fail('rhevm requires a vlan value in provisioning info')

    fill(provisioning_form, provisioning_data, action=provisioning_form.submit_button)
    flash.assert_no_errors()
    request_cells = {
        "Description": "Provision from [{}] to [{}###]".format(template_name, vm_name),
    }
    provision_request = RequestCollection(appliance).instantiate(cells=request_cells)
    yield provision_request

    browser().get(store.base_url)
    appliance.server.login_admin()

    provision_request.remove_request()
    flash.assert_no_errors()


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
    new_vm_name = fauxfactory.gen_alphanumeric(length=16)
    modifications = {"vm_name": new_vm_name}
    new_request = generated_request.copy_request(values=modifications)
    request.addfinalizer(new_request.remove_request())
    assert navigate_to(new_request, 'Details')
