# -*- coding: utf-8 -*-
"""This module contains tests that exercise control of evmserverd service."""
import pytest
from cfme.utils.wait import wait_for_decorator


@pytest.fixture(scope="module")
def start_evmserverd_after_module(appliance):
    appliance.evmserverd.start()
    appliance.wait_for_web_ui()
    yield
    appliance.evmserverd.restart()
    appliance.wait_for_web_ui()


pytestmark = [
    pytest.mark.uncollectif(lambda appliance: appliance.is_pod),
    pytest.mark.usefixtures("start_evmserverd_after_module")
]


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

    Polarion:
        assignee: amavinag
        caseimportance: medium
        initialEstimate: 1/4h
    """

    server_name_key = 'Server'

    server_names = {server[server_name_key] for server in appliance.ssh_client.status["servers"]}
    request.addfinalizer(appliance.evmserverd.start)
    appliance.evmserverd.stop()

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
