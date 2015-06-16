# -*- coding: utf-8 -*-
import pytest
import re
from utils.wait import wait_for


@pytest.yield_fixture(scope="module")
def start_evmserverd_after_module(ssh_client_modscope):
    yield
    ssh_client_modscope.run_command("service evmserverd restart")
    pytest.store.current_appliance.wait_for_web_ui()


pytestmark = [pytest.mark.usefixtures("start_evmserverd_after_module")]


def test_evmserverd_stop(ssh_client):
    """Tests whether stopping the evmserverd really stops the CFME server processes"""
    server_names = {server["Server Name"] for server in ssh_client.status["servers"]}
    assert ssh_client.run_command("service evmserverd stop").rc == 0

    def _check():
        status = {server["Server Name"]: server for server in ssh_client.status["servers"]}
        for server_name in server_names:
            if status[server_name]["Status"] != "stopped":
                return False
        return True

    wait_for(_check, num_sec=120, delay=5, message="servers stopped")


def test_evmserverd_start_twice(ssh_client):
    """If evmserverd start is ran twice, it will then tell that it is already running."""
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
