# -*- coding: utf-8 -*-
"""This module contains tests that exercise control of evmserverd service."""
import pytest
import re
from cfme.utils import version
from cfme.utils.wait import wait_for_decorator


@pytest.yield_fixture(scope="module")
def start_evmserverd_after_module(appliance):
    appliance.start_evm_service()
    appliance.wait_for_web_ui()
    yield
    appliance.restart_evm_service()
    appliance.wait_for_web_ui()


pytestmark = [pytest.mark.usefixtures("start_evmserverd_after_module")]


@pytest.mark.tier(1)
def test_evmserverd_stop(appliance, request):
    """Tests whether stopping the evmserverd really stops the CFME server processes.

    Steps:
        * Remember all server names from ``service evmserverd status`` command.
            * Or the bin/rake evm:status on 5.5+ since the systemd status does not show that, this
                applies also for next references to status.
        * Issue a ``service evmserverd stop`` command.
        * Periodically check output of ``service evmserverd status`` that all servers are stopped.
        * For 5.5+: Really call ``service evmserverd status`` and check that the mentions of
            stopping the service are present.
    """

    server_name_key = version.pick({
        version.LOWEST: 'Server Name',
        '5.8': 'Server'
    })

    server_names = {server[server_name_key] for server in appliance.ssh_client.status["servers"]}
    request.addfinalizer(appliance.start_evm_service)
    appliance.stop_evm_service()

    @wait_for_decorator(timeout="2m", delay=5)
    def servers_stopped():
        status = {
            server[server_name_key]: server for server in appliance.ssh_client.status["servers"]
        }
        for server_name in server_names:
            if status[server_name]["Status"] != "stopped":
                return False
        return True

    status = appliance.ssh_client.run_command("systemctl status evmserverd")
    assert "Stopped EVM server daemon" in status.output
    assert "code=exited" in status.output


@pytest.mark.tier(1)
@pytest.mark.uncollectif(lambda: version.current_version() >= "5.5")
def test_evmserverd_start_twice(appliance, request):
    """If evmserverd start is ran twice, it will then tell that it is already running.

    Steps:
        * Stop the evmserverd using ``service evmserverd stop``.
        * Start the evmserverd using ``service evmserverd start`` command.
        * Assert that the output of the previous command states "Running EVM in background".
        * Start the evmserverd using ``service evmserverd start`` command.
        * Assert that the output of the previous command states "EVM is already running".
        * Extract the PID of the evmserverd from the output from the last command.
        * Verify the process with such PID exists ``kill -0 $PID``.
    """
    request.addfinalizer(appliance.start_evm_service)
    appliance.stop_evm_service()
    # Start first time
    res = appliance.start_evm_service()
    assert "running evm in background" in res.output.lower()
    assert res.rc == 0
    # Start second time
    res = appliance.start_evm_service()
    assert "evm is already running" in res.output.lower()
    assert res.rc == 0
    # Verify the process is running
    pid_match = re.search(r"\(PID=(\d+)\)", res.output)
    assert pid_match is not None
    pid = int(pid_match.groups()[0])
    assert appliance.ssh_client.run_command("kill -0 {}".format(pid)).rc == 0
