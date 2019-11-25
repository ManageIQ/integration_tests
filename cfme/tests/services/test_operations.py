"""Tests checking for link access from outside."""
import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.browser import browser
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="-automate"),  # To prevent the provisioning itself.
    test_requirements.service,
    pytest.mark.provider(classes=[InfraProvider], scope="module", selector=ONE),
    pytest.mark.usefixtures('setup_provider_modscope')
]


@pytest.fixture(scope="module")
def provisioning(provider):
    return provider.data.get("provisioning", {})


@pytest.fixture(scope="module")
def template_name(provisioning):
    return provisioning.get("template")


@pytest.fixture(scope="module")
def vm_name():
    return fauxfactory.gen_alphanumeric(length=16)


@pytest.fixture(scope="module")
def generated_request(appliance, provider, provisioning, template_name, vm_name):
    """Creates a provision request, that is not automatically approved, and returns the search data.

    After finishing the test, request should be automatically deleted.

    Slightly modified code from :py:module:`cfme.tests.infrastructure.test_provisioning`
    """
    if provider.one_of(RHEVMProvider) and provisioning.get('vlan') is None:
        pytest.skip('rhevm requires a vlan value in provisioning info')
    first_name = fauxfactory.gen_alphanumeric()
    last_name = fauxfactory.gen_alphanumeric()
    notes = fauxfactory.gen_alphanumeric()
    e_mail = "{}@{}.test".format(first_name, last_name)
    host, datastore = list(map(provisioning.get, ('host', 'datastore')))
    vm = appliance.collections.infra_vms.instantiate(name=vm_name,
                                                     provider=provider,
                                                     template_name=template_name)
    view = navigate_to(vm.parent, 'Provision')

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
        'network':
            {'vlan': partial_match(provisioning['vlan'] if provisioning.get('vlan') else None)}
    }

    # Same thing, different names. :\
    if provider.one_of(RHEVMProvider):
        provisioning_data['catalog']['provision_type'] = 'Native Clone'
    elif provider.one_of(VMwareProvider):
        provisioning_data['catalog']['provision_type'] = 'VMware'

    # template and provider names for template selection
    provisioning_data['template_name'] = template_name
    provisioning_data['provider_name'] = provider.name

    view.form.fill_with(provisioning_data, on_change=view.form.submit_button)
    request_cells = {
        "Description": "Provision from [{}] to [{}###]".format(template_name, vm_name),
    }
    provision_request = appliance.collections.requests.instantiate(cells=request_cells)
    yield provision_request

    browser().get(appliance.url)
    appliance.server.login_admin()

    provision_request.remove_request()


@pytest.mark.tier(3)
def test_services_request_direct_url(appliance, generated_request):
    """Go to the request page, save the url and try to access it directly.

    Polarion:
        assignee: nansari
        initialEstimate: 1/8h
        casecomponent: Services
    """
    widgetastic = appliance.browser.widgetastic
    selenium = widgetastic.selenium
    assert navigate_to(generated_request, 'Details'), "could not find the request!"
    request_url = selenium.current_url
    navigate_to(appliance.server, 'Configuration')  # Nav to some other page
    selenium.get(request_url)  # Ok, direct access now.
    wait_for(
        lambda: widgetastic.is_displayed("//body[contains(@onload, 'miqOnLoad')]"),
        num_sec=20,
        message="wait for a CFME page appear",
        delay=0.5
    )


@pytest.mark.tier(3)
def test_copy_request(request, generated_request, vm_name, template_name):
    """Check if request gets properly copied.

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
    """
    new_vm_name = '{}-xx'.format(vm_name)
    modifications = {'catalog': {'vm_name': new_vm_name}}
    new_request = generated_request.copy_request(values=modifications)
    request.addfinalizer(new_request.remove_request)
    assert navigate_to(new_request, 'Details')
