import pytest

from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.uncollectif(lambda appliance: appliance.version < "5.9" and appliance.is_pod,
                            reason="5.8 pod appliance doesn't support embedded ansible"),
    pytest.mark.uncollectif(lambda appliance: appliance.version < "5.8",
                            reason="Ansible was added only in 5.8"),
    pytest.mark.ignore_stream("upstream")
]


@pytest.yield_fixture(scope='module')
def enabled_embedded_appliance(appliance):
    """Enables embedded ansible role"""
    appliance.enable_embedded_ansible_role()
    assert appliance.is_embedded_ansible_running
    yield appliance
    appliance.disable_embedded_ansible_role()


def test_embedded_ansible_enable(enabled_embedded_appliance):
    """Tests whether the embedded ansible role and all workers have started correctly"""
    assert wait_for(func=lambda: enabled_embedded_appliance.is_embedded_ansible_running, num_sec=30)
    assert wait_for(func=lambda: enabled_embedded_appliance.is_rabbitmq_running, num_sec=30)
    assert wait_for(func=lambda: enabled_embedded_appliance.is_nginx_running, num_sec=30)
    endpoint = 'api' if enabled_embedded_appliance.is_pod else 'ansibleapi'
    assert enabled_embedded_appliance.ssh_client.run_command(
        'curl -kL https://localhost/{endp} | grep "Ansible Tower REST API"'.format(endp=endpoint),
        container=enabled_embedded_appliance._ansible_pod_name)


def test_embedded_ansible_disable(enabled_embedded_appliance):
    """Tests whether the embedded ansible role and all workers have stopped correctly"""
    assert wait_for(func=lambda: enabled_embedded_appliance.is_rabbitmq_running, num_sec=30)
    assert wait_for(func=lambda: enabled_embedded_appliance.is_nginx_running, num_sec=30)
    enabled_embedded_appliance.disable_embedded_ansible_role()

    def is_supervisord_stopped(enabled_embedded_appliance):
        """Checks if supervisord has stopped"""
        result = enabled_embedded_appliance.ssh_client.run_command(
            'systemctl status supervisord | grep inactive',
            container=enabled_embedded_appliance._ansible_pod_name)
        return result.success

    def is_rabbitmq_stopped(enabled_embedded_appliance):
        """Checks if rabbitmq-server has stopped"""
        result = enabled_embedded_appliance.ssh_client.run_command(
            'systemctl status rabbitmq-server | grep inactive',
            container=enabled_embedded_appliance._ansible_pod_name)
        return result.success

    def is_nginx_stopped(enabled_embedded_appliance):
        """Checks if nginx has stopped"""
        result = enabled_embedded_appliance.ssh_client.run_command(
            'systemctl status nginx | grep inactive',
            container=enabled_embedded_appliance._ansible_pod_name)
        return result.success

    def is_ansible_pod_stopped(enabled_embedded_appliance):
        # todo: implement appropriate methods in appliance
        return enabled_embedded_appliance.ssh_client.run_command('oc get pods|grep ansible',
                                                                 ensure_host=True).failed

    if not enabled_embedded_appliance.is_pod:
        assert wait_for(is_supervisord_stopped, func_args=[enabled_embedded_appliance], num_sec=180)
        assert wait_for(is_rabbitmq_stopped, func_args=[enabled_embedded_appliance], num_sec=60)
        assert wait_for(is_nginx_stopped, func_args=[enabled_embedded_appliance], num_sec=30)
    else:
        assert wait_for(is_ansible_pod_stopped, func_args=[enabled_embedded_appliance], num_sec=180)
