import pytest

from utils.version import current_version


@pytest.fixture(scope='module')
def enabled_embedded_appliance(temp_appliance_preconfig):
    roles = temp_appliance_preconfig.server_roles
    roles['embedded_ansible'] = True
    temp_appliance_preconfig.server_roles = roles
    temp_appliance_preconfig.wait_for_embedded_ansible()
    assert temp_appliance_preconfig.is_embedded_ansible_running
    return temp_appliance_preconfig


@pytest.mark.smoke
@pytest.mark.ignore_stream("upstream")
@pytest.mark.uncollectif(lambda: current_version() < "5.8")
def test_embedded_ansible_enable(enabled_embedded_appliance):
    assert enabled_embedded_appliance.is_embedded_ansible_running
    assert enabled_embedded_appliance.is_rabbitmq_running
    assert enabled_embedded_appliance.is_nginx_running
    assert enabled_embedded_appliance.ssh_client.run_command(
        'curl -kL https://localhost/ansibleapi | grep "Ansible Tower REST API"')
    return_code, output = enabled_embedded_appliance.ssh_client.run_rails_command(
        "EmbeddedAnsible.alive?")
    assert 'True' in output
