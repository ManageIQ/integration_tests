# -*- coding: utf-8 -*-
import pytest

from cfme.cloud.provider import CloudProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils import conf
from cfme.utils.generators import random_vm_name
from cfme.utils.providers import get_mgmt
from cfme.utils.ssh import SSHClient
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([CloudProvider], selector=ONE, scope='module'),
    pytest.mark.usefixtures('setup_provider_modscope')
]


@pytest.fixture(scope='module')
def proxy_machine():
    """ Deploy vm for proxy test

    This fixture uses for deploy vm on provider from yaml and then receive it's ip
    After test run vm deletes from provider
    """
    depot_machine_name = random_vm_name('proxy')
    data = conf.cfme_data.get("proxy_template")
    proxy_provider_key = data["provider"]
    proxy_template_name = data["template_name"]
    proxy_port = data['port']
    prov = get_mgmt(proxy_provider_key)
    deploy_template(proxy_provider_key,
                    depot_machine_name,
                    template_name=proxy_template_name)
    yield prov.get_ip_address(depot_machine_name), proxy_port
    prov.delete_vm(depot_machine_name)


@pytest.fixture(scope='module')
def proxy_ssh(proxy_machine):
    proxy_ip, __ = proxy_machine
    with SSHClient(
            hostname=proxy_ip,
            **conf.credentials['proxy_vm']) as ssh_client:
        yield ssh_client


def validate_proxy_logs(provider, proxy_ssh, appliance_ip):

    def _is_ip_in_log():
        provider.refresh_provider_relationships()
        return proxy_ssh.run_command(
            "grep {} /var/log/squid/access.log".format(appliance_ip)).success

    # need to wait until requests will occur in access.log or check if its empty after some time
    wait_for(func=_is_ip_in_log, num_sec=300, delay=10,
             message='Waiting for requests from appliance in logs')


@pytest.fixture(scope="function")
def prepare_proxy(proxy_ssh, provider, appliance):
    proxy_ssh.run_command('echo "" > /var/log/squid/access.log')
    yield
    appliance.set_proxy(None, None, prov_type=provider.type)


def test_proxy_valid(appliance, proxy_machine, proxy_ssh, prepare_proxy, provider):
    proxy_ip, proxy_port = proxy_machine
    prov_type = provider.type
    appliance.set_proxy(proxy_ip, proxy_port, prov_type=prov_type)
    validate_proxy_logs(provider, proxy_ssh, appliance.hostname)


def test_proxy_invalid(appliance, proxy_machine, prepare_proxy, provider):
    proxy_ip, proxy_port = proxy_machine
    prov_type = provider.type
    appliance.set_proxy('1.1.1.1', proxy_port, prov_type=prov_type)
    provider.refresh_provider_relationships()
    wait_for(
        provider.is_refreshed,
        func_kwargs={"refresh_delta": 120},
        fail_condition=True,
        num_sec=240,
        delay=30
    )
