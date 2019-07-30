import pytest

from cfme import test_requirements
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [pytest.mark.ignore_stream("upstream"), test_requirements.ansible]


@pytest.fixture(scope="function")
def embedded_appliance(appliance):
    appliance.enable_embedded_ansible_role()
    assert appliance.is_embedded_ansible_running
    yield appliance
    appliance.disable_embedded_ansible_role()


@pytest.mark.tier(3)
def test_embedded_ansible_enable(embedded_appliance):
    """Tests whether the embedded ansible role and all workers have started correctly

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    assert wait_for(lambda: embedded_appliance.is_embedded_ansible_running, num_sec=30)
    if embedded_appliance.version < "5.11":
        assert wait_for(lambda: embedded_appliance.supervisord.is_active, num_sec=30)
        assert wait_for(lambda: embedded_appliance.rabbitmq_server.running, num_sec=30)
        assert wait_for(lambda: embedded_appliance.nginx.running, num_sec=30)
        endpoint = "api" if embedded_appliance.is_pod else "ansibleapi"

        assert embedded_appliance.ssh_client.run_command(
            'curl -kL https://localhost/{endp} | grep "AWX REST API"'.format(endp=endpoint),
            container=embedded_appliance.ansible_pod_name,
        )


@pytest.mark.tier(3)
def test_embedded_ansible_disable(embedded_appliance):
    """Tests whether the embedded ansible role and all workers have stopped correctly

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    if embedded_appliance.version < "5.11":
        assert wait_for(lambda: embedded_appliance.rabbitmq_server.running, num_sec=30)
        assert wait_for(lambda: embedded_appliance.nginx.running, num_sec=30)
    assert embedded_appliance.disable_embedded_ansible_role()

    if not embedded_appliance.is_pod and embedded_appliance.version < "5.11":
        assert wait_for(
            lambda: not embedded_appliance.supervisord.is_active, num_sec=180
        )
        assert wait_for(
            lambda: not embedded_appliance.rabbitmq_server.is_active, num_sec=80
        )
        assert wait_for(lambda: not embedded_appliance.nginx.is_active, num_sec=30)
    else:
        assert wait_for(lambda: embedded_appliance.is_ansible_pod_stopped, num_sec=300)


@pytest.mark.tier(1)
def test_embedded_ansible_event_catcher_process(embedded_appliance):
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
    if embedded_appliance.version < "5.11":
        result = embedded_appliance.ssh_client.run_rake_command(
            "evm:status | grep 'EmbeddedAnsible'"
        ).output

        for data in result.splitlines():
            logger.info("Checking service/process %s started or not", data)
            assert "started" in data
    else:
        rpm_check = embedded_appliance.ssh_client.run_command(
            "rpm -qa | grep 'ansible-runner'"
        ).output

        for data in rpm_check.splitlines():
            logger.info("Checking %s is present or not", data)
            assert "ansible-runner" in data


@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.11")
def test_embedded_ansible_logs(embedded_appliance):
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
    tower_log_folder = embedded_appliance.ssh_client.run_command("ls /var/log/tower/")
    assert tower_log_folder.success

    logs = tower_log_folder.output.splitlines()
    diff = tuple(set(logs) - set(log_checks))
    # Asserting all files except setup file.
    assert 1 == len(diff)
    # Retrieving setup log file from list and asserting with length
    # Setup log file contains date/time string in it.
    assert "setup" in diff[0]
