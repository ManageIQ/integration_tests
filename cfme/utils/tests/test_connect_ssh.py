from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import PropertyMock

import pytest

from cfme.utils.ssh import connect_ssh


creds = SimpleNamespace(principal='mockuser', secret='mockpass')


@pytest.fixture(autouse=True)
def nosleep(mocker):
    mocker.patch('time.sleep')


@pytest.fixture
def vm_mock():
    vm = Mock()
    all_ips_mock = PropertyMock()
    type(vm).all_ips = all_ips_mock
    all_ips_mock.side_effect = [
        [None],
        ['NOT_WORKING_IP_MOCK'],
        ['NOT_WORKING_IP_MOCK', 'OTHER_NOT_WORKING_IP_MOCK',
            'WORKING_IP_MOCK', 'SHOULD_NOT_REACH_THIS_MOCK'],
        ['SHOULD_NOT_REACH_THIS_MOCK', 'SHOULD_NOT_REACH_THIS_MOCK']
    ]
    return vm


@pytest.fixture
def vm_mock2():
    vm = Mock()
    all_ips_mock = PropertyMock()
    type(vm).all_ips = all_ips_mock
    all_ips_mock.side_effect = [
        ['WORKING_IP_MOCK', 'SHOULD_NOT_REACH_THIS_MOCK']
    ]
    return vm


class SSHClientMock:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.close = Mock()
        self.run_command = Mock()
        self.run_command.success.return_value = True

        # disabling check_port is required for not making repeated connection
        # attempts in the SSHClient
        assert kwargs['use_check_port'] is False

    def connect(self):
        hostname = self.kwargs['hostname']
        if hostname == 'WORKING_IP_MOCK':
            return self
        elif hostname == 'SHOULD_NOT_REACH_THIS_MOCK':
            pytest.fail('We should not have reached checking this IP!')
        else:
            raise Exception(f'This was raised for IP {hostname}.')


def test_connect_ssh(mocker, vm_mock, vm_mock2):
    mocker.patch('cfme.utils.ssh.SSHClient', SSHClientMock)
    assert connect_ssh(vm_mock, creds, num_sec=3, connect_timeout=1, delay=1).run_command()
    assert connect_ssh(vm_mock2, creds, num_sec=3, connect_timeout=1, delay=1).run_command()
