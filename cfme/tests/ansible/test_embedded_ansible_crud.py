import pytest

from cfme.utils.version import current_version
from cfme.utils.wait import wait_for


@pytest.yield_fixture(scope='module')
def enabled_embedded_appliance(appliance):
    """Enables embedded ansible role"""
    appliance.enable_embedded_ansible_role()
    assert appliance.is_embedded_ansible_running
    yield appliance
    appliance.disable_embedded_ansible_role()


@pytest.mark.ignore_stream("upstream")
@pytest.mark.uncollectif(lambda: current_version() < "5.8")
def test_embedded_ansible_enable(enabled_embedded_appliance):
    """Tests whether the embedded ansible role and all workers have started correctly"""
    assert wait_for(func=lambda: enabled_embedded_appliance.is_embedded_ansible_running, num_sec=30)
    assert wait_for(func=lambda: enabled_embedded_appliance.is_rabbitmq_running, num_sec=30)
    assert wait_for(func=lambda: enabled_embedded_appliance.is_nginx_running, num_sec=30)
    assert enabled_embedded_appliance.ssh_client.run_command(
        'curl -kL https://localhost/ansibleapi | grep "Ansible Tower REST API"',
        container=enabled_embedded_appliance._ansible_pod_name)


@pytest.mark.ignore_stream("upstream")
@pytest.mark.uncollectif(lambda: current_version() < "5.8")
def test_embedded_ansible_disable(enabled_embedded_appliance):
    """Tests whether the embedded ansible role and all workers have stopped correctly"""
    assert wait_for(func=lambda: enabled_embedded_appliance.is_rabbitmq_running, num_sec=30)
    assert wait_for(func=lambda: enabled_embedded_appliance.is_nginx_running, num_sec=30)
    enabled_embedded_appliance.disable_embedded_ansible_role()

    def is_superviserd_stopped(enabled_embedded_appliance):
        """Checks if supervisord has stopped"""
        return_code, output = enabled_embedded_appliance.ssh_client.run_command(
            'systemctl status supervisord | grep inactive',
            container=enabled_embedded_appliance._ansible_pod_name)
        return return_code == 0

    def is_rabbitmq_stopped(enabled_embedded_appliance):
        """Checks if rabbitmq-server has stopped"""
        return_code, output = enabled_embedded_appliance.ssh_client.run_command(
            'systemctl status rabbitmq-server | grep inactive',
            container=enabled_embedded_appliance._ansible_pod_name)
        return return_code == 0

    def is_nginx_stopped(enabled_embedded_appliance):
        """Checks if nginx has stopped"""
        return_code, output = enabled_embedded_appliance.ssh_client.run_command(
            'systemctl status nginx | grep inactive',
            container=enabled_embedded_appliance._ansible_pod_name)
        return return_code == 0

    assert wait_for(is_superviserd_stopped, func_args=[enabled_embedded_appliance], num_sec=180)
    assert wait_for(is_rabbitmq_stopped, func_args=[enabled_embedded_appliance], num_sec=60)
    assert wait_for(is_nginx_stopped, func_args=[enabled_embedded_appliance], num_sec=30)
