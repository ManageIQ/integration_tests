import pytest

from cfme.utils.version import current_version
from cfme.utils.wait import wait_for


@pytest.fixture(scope='module')
def enabled_embedded_appliance(temp_appliance_preconfig):
    """Takes a preconfigured appliance and enables the embedded ansible role"""
    temp_appliance_preconfig.enable_embedded_ansible_role()
    assert temp_appliance_preconfig.is_embedded_ansible_running
    return temp_appliance_preconfig


@pytest.mark.ignore_stream("upstream")
@pytest.mark.uncollectif(lambda: current_version() < "5.8")
def test_embedded_ansible_enable(enabled_embedded_appliance):
    """Tests wether the embedded ansible role and all workers have started correctly"""
    assert wait_for(func=lambda: enabled_embedded_appliance.is_embedded_ansible_running, num_sec=30)
    assert wait_for(func=lambda: enabled_embedded_appliance.is_rabbitmq_running, num_sec=30)
    assert wait_for(func=lambda: enabled_embedded_appliance.is_nginx_running, num_sec=30)
    assert enabled_embedded_appliance.ssh_client.run_command(
        'curl -kL https://localhost/ansibleapi | grep "Ansible Tower REST API"')
