# -*- coding: utf-8 -*-
"""This module contains tests that exercise control of evmserverd service."""
import pytest
import re
from utils.version import current_version


@pytest.yield_fixture(scope="module")
def start_evmserverd_after_module(ssh_client_modscope):
    ssh_client_modscope.run_command("service evmserverd start")
    pytest.store.current_appliance.wait_for_web_ui()
    yield
    ssh_client_modscope.run_command("service evmserverd restart")
    pytest.store.current_appliance.wait_for_web_ui()


pytestmark = [pytest.mark.usefixtures("start_evmserverd_after_module")]


@pytest.mark.tier(1)
def test_evmserverd_stop(ssh_client):
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
    server_names = {server["Server Name"] for server in ssh_client.status["servers"]}
    assert ssh_client.run_command("service evmserverd stop").rc == 0

    @pytest.wait_for(timeout="2m", delay=5)
    def servers_stopped():
        status = {server["Server Name"]: server for server in ssh_client.status["servers"]}
        for server_name in server_names:
            if status[server_name]["Status"] != "stopped":
                return False
        return True

    if current_version() >= "5.5":
        status = ssh_client.run_command("service evmserverd status")
        assert "Stopped EVM server daemon" in status.output
        assert "code=exited" in status.output


@pytest.mark.tier(1)
@pytest.mark.uncollectif(lambda: current_version() >= "5.5")
def test_evmserverd_start_twice(ssh_client):
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
    assert ssh_client.run_command("service evmserverd stop").rc == 0
    # Start first time
    res = ssh_client.run_command("service evmserverd start")
    assert "running evm in background" in res.output.lower()
    assert res.rc == 0
    # Start second time
    res = ssh_client.run_command("service evmserverd start")
    assert "evm is already running" in res.output.lower()
    assert res.rc == 0
    # Verify the process is running
    pid_match = re.search(r"\(PID=(\d+)\)", res.output)
    assert pid_match is not None
    pid = int(pid_match.groups()[0])
    assert ssh_client.run_command("kill -0 {}".format(pid)).rc == 0
