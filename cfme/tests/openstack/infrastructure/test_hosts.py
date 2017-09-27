import pytest

from cfme.configure.tasks import is_host_analysis_finished
from cfme.infrastructure.host import Host
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.web_ui import toolbar
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')
pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


def test_host_configuration(provider, soft_assert):
    view = navigate_to(provider, 'ProviderNodes')
    entity_names = view.entities.all_entity_names
    assert len(entity_names) > 0
    for entity_name in entity_names:
        host = Host(name=entity_name, provider=provider)
        host.run_smartstate_analysis()
        wait_for(is_host_analysis_finished, [host.name], delay=15,
                 timeout="10m", fail_func=toolbar.refresh)
        fields = ['Packages', 'Services', 'Files']
        for field in fields:
            value = int(host.get_detail("Configuration", field))
            soft_assert(value > 0, 'Nodes number of {} is 0'.format(field))


def test_host_cpu_resources(provider, soft_assert):
    view = navigate_to(provider, 'ProviderNodes')
    entity_names = view.entities.all_entity_names
    assert len(entity_names) > 0
    for entity_name in entity_names:
        host = Host(name=entity_name, provider=provider)
        fields = ['Number of CPUs', 'Number of CPU Cores',
                  'CPU Cores Per Socket']
        for field in fields:
            value = int(host.get_detail("Properties", field))
            soft_assert(value > 0, "Aggregate Node {} is 0".format(field))


def test_host_auth(provider, soft_assert):
    view = navigate_to(provider, 'ProviderNodes')
    entity_names = view.entities.all_entity_names
    assert len(entity_names) > 0
    for entity_name in entity_names:
        host = Host(name=entity_name, provider=provider)
        navigate_to(host, 'Details')
        auth_status = host.get_detail('Authentication Status', 'SSH Key Pair Credentials')
        soft_assert(auth_status == 'Valid',
                    'Incorrect SSH authentication status {}'.format(auth_status))


def test_host_devices(provider):
    view = navigate_to(provider, 'ProviderNodes')
    entity_names = view.entities.all_entity_names
    assert len(entity_names) > 0
    for entity_name in entity_names:
        host = Host(name=entity_name, provider=provider)
        assert int(host.get_detail("Properties", "Devices")) > 0


def test_host_hostname(provider, soft_assert):
    view = navigate_to(provider, 'ProviderNodes')
    entity_names = view.entities.all_entity_names
    assert len(entity_names) > 0
    for entity_name in entity_names:
        host = Host(name=entity_name, provider=provider)
        result = host.get_detail("Properties", "Hostname")
        soft_assert(result, "Missing hostname in: " + str(result))


def test_host_memory(provider):
    view = navigate_to(provider, 'ProviderNodes')
    entity_names = view.entities.all_entity_names
    assert len(entity_names) > 0
    for entity_name in entity_names:
        host = Host(name=entity_name, provider=provider)
        result = int(host.get_detail("Properties", "Memory").split()[0])
        assert result > 0


def test_host_security(provider, soft_assert):
    view = navigate_to(provider, 'ProviderNodes')
    entity_names = view.entities.all_entity_names
    assert len(entity_names) > 0
    for entity_name in entity_names:
        host = Host(name=entity_name, provider=provider)
        soft_assert(
            int(host.get_detail("Security", "Users")) > 0,
            'Nodes number of Users is 0')

        soft_assert(
            int(host.get_detail("Security", "Groups")) > 0,
            'Nodes number of Groups is 0')


def test_host_smbios_data(provider, soft_assert):
    """Checks that Manufacturer/Model values are shown for each infra node"""
    view = navigate_to(provider, 'ProviderNodes')
    entity_names = view.entities.all_entity_names
    assert len(entity_names) > 0
    for entity_name in entity_names:
        host = Host(entity_name, provider=provider)
        navigate_to(host, 'Details')
        res = host.get_detail('Properties', 'Manufacturer / Model')
        soft_assert(res, 'Manufacturer / Model value are empty')
        soft_assert(res != 'N/A')


def test_host_zones_assigned(provider):
    view = navigate_to(provider, 'ProviderNodes')
    entity_names = [en for en in view.entities.all_entity_names if 'Compute' in en]
    assert len(entity_names) > 0
    for entity_name in entity_names:
        host = Host(name=entity_name, provider=provider)
        result = host.get_detail('Relationships', 'Availability Zone')
        assert result, "Availability zone doesn't specified"
