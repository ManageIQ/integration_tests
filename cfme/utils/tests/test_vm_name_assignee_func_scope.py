"""Manual VMware Provider tests"""
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider

pytestmark = [
    test_requirements.vmware,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('setup_provider', 'uses_infra_providers'),
    pytest.mark.provider([VMwareProvider],
                        required_fields=[['provisioning', 'template'],
                                        ['provisioning', 'host'],
                                        ['provisioning', 'datastore'],
                                        (["cap_and_util", "capandu_vm"], "cu-24x7")],
                        scope="module")
]


@pytest.mark.parametrize('create_vm', ['small_template'], indirect=True)
def test_vm_name_postfix_1(appliance, create_vm, provider):
    """
    Test the HTML5 console support for a particular provider.

    The supported providers are:

        VMware
        Openstack
        RHV

    For a given provider, and a given VM, the console will be opened, and then:

        - The console's status will be checked.
        - A command that creates a file will be sent through the console.
        - Using ssh we will check that the command worked (i.e. that the file
          was created.

    Polarion:
        assignee: KK
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    provider.appliance.provider_based_collection(provider)


@pytest.mark.parametrize('create_vm', ['small_template'], indirect=True)
def test_vm_name_postfix_2(appliance, create_vm, provider):
    """
    Test the HTML5 console support for a particular provider.

    The supported providers are:

        VMware
        Openstack
        RHV

    For a given provider, and a given VM, the console will be opened, and then:

        - The console's status will be checked.
        - A command that creates a file will be sent through the console.
        - Using ssh we will check that the command worked (i.e. that the file
          was created.

    Polarion:
        assignee: KKULKARN
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    provider.appliance.provider_based_collection(provider)
