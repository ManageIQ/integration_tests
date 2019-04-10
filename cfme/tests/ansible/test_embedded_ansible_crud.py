import pytest

from cfme import test_requirements
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    test_requirements.ansible,
]


@pytest.fixture(scope='module')
def enabled_embedded_appliance(appliance):
    """Enables embedded ansible role via UI"""
    appliance.enable_embedded_ansible_role()
    assert appliance.is_embedded_ansible_running
    yield appliance
    appliance.disable_embedded_ansible_role()


@pytest.mark.tier(3)
def test_embedded_ansible_enable(enabled_embedded_appliance):
    """Tests whether the embedded ansible role and all workers have started correctly

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    assert wait_for(func=lambda: enabled_embedded_appliance.is_embedded_ansible_running, num_sec=30)
    assert wait_for(func=lambda: enabled_embedded_appliance.is_rabbitmq_running, num_sec=30)
    assert wait_for(func=lambda: enabled_embedded_appliance.is_nginx_running, num_sec=30)
    endpoint = "api" if enabled_embedded_appliance.is_pod else "ansibleapi"

    assert enabled_embedded_appliance.ssh_client.run_command(
        'curl -kL https://localhost/{endp} | grep "AWX REST API"'.format(endp=endpoint),
        container=enabled_embedded_appliance._ansible_pod_name)


@pytest.mark.tier(3)
def test_embedded_ansible_disable(enabled_embedded_appliance):
    """Tests whether the embedded ansible role and all workers have stopped correctly

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/6h
        tags: ansible_embed
    """
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


@pytest.mark.tier(1)
def test_embedded_ansible_event_catcher_process(enabled_embedded_appliance):
    """
    EventCatcher process is started after Ansible role is enabled (rails
    evm:status)

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/4h
        tags: ansible_embed
    """
    result = enabled_embedded_appliance.ssh_client.run_rake_command(
        "evm:status | grep 'EmbeddedAnsible'"
    ).output

    for data in result.splitlines():
        logger.info("Checking service/process %s started or not", data)
        assert "started" in data


@pytest.mark.tier(1)
def test_embedded_ansible_logs(enabled_embedded_appliance):
    """
    Separate log files should be generated for Ansible to aid debugging.
    p1 (/var/log/tower)

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/4h
        tags: ansible_embed
    """
    log_checks = [
        "callback_receiver.log",
        "dispatcher.log",
        "fact_receiver.log",
        "management_playbooks.log",
        "task_system.log",
        "tower.log",
        "tower_rbac_migrations.log",
        "tower_system_tracking_migrations.log",
    ]

    # Asserting log folder is present
    tower_log_folder = enabled_embedded_appliance.ssh_client.run_command(
        "ls /var/log/tower/"
    )
    assert tower_log_folder.success

    logs = tower_log_folder.output.splitlines()
    diff = tuple(set(logs) - set(log_checks))
    # Asserting all files except setup file.
    assert 1 == len(diff)
    # Retriving setup log file from list and asserting with length
    # Setup log file contains date/time string in it.
    assert "setup" in diff[0]
