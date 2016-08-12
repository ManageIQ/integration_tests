# -*- coding: utf-8 -*-
"""Tests checking for link access from outside."""
from __future__ import unicode_literals
import fauxfactory
import pytest

import cfme.provisioning
from cfme.fixtures import pytest_selenium as sel
from cfme.login import login_admin
from cfme.provisioning import provisioning_form
from cfme.services import requests
from cfme.web_ui import flash
from utils.browser import browser
from utils.providers import setup_a_provider
from utils.wait import wait_for
from fixtures.pytest_store import store


pytestmark = [
    pytest.mark.meta(server_roles="-automate"),  # To prevent the provisioning itself.
]


@pytest.fixture(scope="module")
def provider():
    return setup_a_provider("infra")


@pytest.fixture(scope="module")
def provider_data(provider):
    return provider.get_yaml_data()


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
def generated_request(provider, provider_data, provisioning, template_name, vm_name):
    """Creates a provision request, that is not automatically approved, and returns the search data.

    After finishing the test, request should be automatically deleted.

    Slightly modified code from :py:module:`cfme.tests.infrastructure.test_provisioning`
    """
    first_name = fauxfactory.gen_alphanumeric()
    last_name = fauxfactory.gen_alphanumeric()
    notes = fauxfactory.gen_alphanumeric()
    e_mail = "{}@{}.test".format(first_name, last_name)
    host, datastore = map(provisioning.get, ('host', 'datastore'))
    pytest.sel.force_navigate('infrastructure_provision_vms', context={
        'provider': provider,
        'template_name': template_name,
    })

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

    provisioning_form.fill(provisioning_data)
    pytest.sel.click(provisioning_form.submit_button)
    flash.assert_no_errors()
    request_cells = {
        "Description": "Provision from [{}] to [{}###]".format(template_name, vm_name),
    }
    yield request_cells

    browser().get(store.base_url)
    login_admin()

    requests.delete_request(request_cells)
    flash.assert_no_errors()


@pytest.mark.tier(3)
def test_services_request_direct_url(generated_request):
    """Go to the request page, save the url and try to access it directly."""
    assert requests.go_to_request(generated_request), "could not find the request!"
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
    cfme.provisioning.copy_request_by_vm_and_template_name(
        vm_name, template_name, {"vm_name": new_vm_name}, multi=True)
    request.addfinalizer(lambda: requests.delete_request({
        "Description": "Provision from [{}] to [{}###]".format(template_name, new_vm_name),
    }))
    assert cfme.provisioning.go_to_request_by_vm_and_template_name(
        new_vm_name, template_name, multi=True)
