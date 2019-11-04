# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from widgetastic_patternfly import DropdownItemNotFound

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter


filter_fields = {
    'required_fields': [['provisioning', 'template'],
                        ['provisioning', 'host'],
                        ['provisioning', 'datastore']],
}
infra_filter = ProviderFilter(classes=[InfraProvider], **filter_fields)
not_vmware = ProviderFilter(classes=[VMwareProvider], inverted=True)

pytestmark = [
    pytest.mark.meta(roles="+automate"),
    pytest.mark.provider(gen_func=providers, filters=[infra_filter], scope='module'),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.long_running,
]


@pytest.fixture(scope="function")
def clone_vm_name():
    clone_vm_name = 'test_cloning_{}'.format(fauxfactory.gen_alphanumeric())
    return clone_vm_name


@pytest.fixture
def create_vm(appliance, provider, request):
    """Fixture to provision vm to the provider being tested"""
    vm_name = 'test_clone_{}'.format(fauxfactory.gen_alphanumeric())
    vm = appliance.collections.infra_vms.instantiate(vm_name, provider)
    logger.info("provider_key: %s", provider.key)

    if not provider.mgmt.does_vm_exist(vm.name):
        logger.info("deploying %s on provider %s", vm.name, provider.key)
        vm.create_on_provider(allow_skip="default", find_in_cfme=True)
    yield vm
    vm.cleanup_on_provider()


@pytest.mark.provider([VMwareProvider], override=True, **filter_fields)
@pytest.mark.meta(blockers=[BZ(1685201)])
@test_requirements.provision
def test_vm_clone(appliance, provider, clone_vm_name, create_vm):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    provision_type = 'VMware'
    create_vm.clone_vm("email@xyz.com", "first", "last", clone_vm_name, provision_type)
    request_description = clone_vm_name
    request_row = appliance.collections.requests.instantiate(request_description,
                                                             partial_check=True)
    request_row.wait_for_request(method='ui')
    msg = "Request failed with the message {}".format(request_row.row.last_message.text)
    assert request_row.is_succeeded(method='ui'), msg


@pytest.mark.rhv3
@pytest.mark.provider(gen_func=providers,
                      filters=[infra_filter, not_vmware],
                      override=True)
@test_requirements.provision
def test_vm_clone_neg(provider, clone_vm_name, create_vm):
    """Tests that we can't clone non-VMware VM

    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    provision_type = 'VMware'
    with pytest.raises(DropdownItemNotFound):
        create_vm.clone_vm("email@xyz.com", "first", "last", clone_vm_name, provision_type)
