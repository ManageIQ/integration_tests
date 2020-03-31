""" The utility_vm is a vm that is meant to serve various services that the
tests are requiring.

The VM is spawned from the template that can be prepared using tooling in
`scripts/utility-vm`. There is a README that you should read to get more info.

When the VM is created, we need to find the IP to conenct to. The  This is done by
attempting to create a tcp connection to an IPs retrieved from the provider the
VM was spawned on. Each service is on different port so there are fixtures for
obtaining the IP for each service.

Note it may not be possible to use ping to find the VM responding as the ping
may not be available in the docker image. But TCP certainly will be available.

Note that using ping is also problematic because the OS may be responing on
ping, but the required service may not be up and ready.
"""
import os.path
import time
from contextlib import contextmanager

import pytest

from cfme.base.credential import SSHCredential
from cfme.utils.conf import cfme_data
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.net import net_check
from cfme.utils.ssh import SSHClient
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import TimedOutError


def _trying_ips(vm, attempts=60, interval=10):
    for attempt in range(attempts):
        for ip in getattr(vm, 'all_ips', []):
            yield ip
            return
        time.sleep(interval)


@contextmanager
def connect_ssh(vm, creds):
    for ip in _trying_ips(vm):
        try:
            with SSHClient(hostname=ip, username=creds.principal, password=creds.secret) as client:
                logger.info("SSH connected to IP %s", ip)
                result = client.run_command("true")
                if not result.success:
                    raise Exception(f"Command `true` failed on ip {ip}.")
                yield client
                return
        except Exception as ex:
            logger.info("Failed to connect with SSH to %s: %s", ip, ex)
    else:
        raise TimedOutError(f"Coudln't find an IP responding to ssh for vm {vm}")


def _pick_responding_ip(vm, port):
    for ip in _trying_ips(vm):
        if net_check(port, ip):
            return ip
    else:
        raise TimedOutError(f"Coudln't find an IP of vm {vm} with port {port} responding")


@pytest.fixture
def utility_vm_nfs_ip(utility_vm):
    vm, _, _ = utility_vm
    one_of_the_nfs_ports = 111
    yield _pick_responding_ip(vm, one_of_the_nfs_ports)


@pytest.fixture
def utility_vm_samba_ip(utility_vm):
    vm, _, _ = utility_vm
    yield _pick_responding_ip(vm, 445)


@pytest.fixture(scope='module')
def utility_vm_proxy_data(utility_vm):
    vm, __, data = utility_vm
    yield _pick_responding_ip(vm, data.proxy.port), data.proxy.port


@pytest.fixture(scope='module')
def utility_vm_ssh(utility_vm):
    vm, injected_user_cred, __ = utility_vm
    ip = _pick_responding_ip(vm, 22)

    with SSHClient(
            hostname=ip,
            username=injected_user_cred.principal,
            password=injected_user_cred.secret) as ssh_client:
        yield ssh_client


@pytest.fixture(scope='module')
def utility_vm():
    """ Deploy an utility vm for tests to use.

    This fixture creates a vm on provider and then receives its ip.
    After the test run vm is deleted from provider.
    """
    try:
        data = cfme_data['utility_vm']
        injected_user_cred = SSHCredential.from_config(data['injected_credentials'])
        try:
            with open(os.path.expanduser('~/.ssh/id_rsa.pub')) as f:
                authorized_ssh_keys = f.read()
        except FileNotFoundError:
            authorized_ssh_keys = None
        vm = deploy_template(
            data.provider,
            random_vm_name('proxy'),
            template_name=data.template_name,
            # The naming is not great. It comes from
            # https://access.redhat.com/documentation/en-us/red_hat_virtualization/4.2/
            # html-single/python_sdk_guide/index#Starting_a_Virtual_Machine_with_Cloud-Init
            initialization=dict(
                user_name=injected_user_cred.principal,
                root_password=injected_user_cred.secret,
                authorized_ssh_keys=authorized_ssh_keys)
        )
    except AttributeError:
        msg = 'Missing utility_vm data from cfme_data.yaml, cannot deploy the utility vm.'
        logger.exception(msg)
        pytest.skip(msg)

    yield vm, injected_user_cred, data

    vm.delete()
