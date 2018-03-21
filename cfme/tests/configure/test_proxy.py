# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.utils import conf
from cfme.utils.providers import get_mgmt
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.ssh import SSHClient


@pytest.yield_fixture(scope="module")
def proxy_machine():
    """ Deploy vm for proxy test

    This fixture uses for deploy vm on provider from yaml and then receive it's ip
    After test run vm deletes from provider
    """
    depot_machine_name = "test_long_proxy_{}".format(fauxfactory.gen_alphanumeric())
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


def validate_provider(provider, valid_proxy=True):
    provider.is_refreshed()
    result = provider.last_refresh_error() is None if valid_proxy else provider.last_refresh_error()
    assert result


def validate_proxy_logs(proxy_ip, appliance_ip, valid_proxy=True):
    proxy_ssh = SSHClient(hostname=proxy_ip, **conf.credentials['proxy_vm'])
    log_file = proxy_ssh.run_command("cat /var/log/squid/access.log").output
    assert (appliance_ip in log_file) == valid_proxy


@pytest.yield_fixture(scope="function")
def prepare_proxy(proxy_machine):
    proxy_ip, proxy_port = proxy_machine
    proxy_ssh = SSHClient(hostname=proxy_ip, **conf.credentials['proxy_vm'])
    proxy_ssh.run_command("echo "" >> /var/log/squid/access.log")
    yield
    proxy_ssh.run_command("echo "" >> /var/log/squid/access.log")


def test_proxy_valid(appliance, proxy_machine, prepare_proxy, provider, request):
    proxy_ip, proxy_port = proxy_machine
    prov_type = provider.type
    appliance.set_proxy(proxy_ip, proxy_port, prov_type=prov_type)
    request.addfinalizer(lambda: appliance.set_proxy(None, None, prov_type=prov_type))
    validate_provider(provider)
    validate_proxy_logs(proxy_ip, appliance.hostname)


def test_proxy_invalid(appliance, proxy_machine, prepare_proxy, provider, request):
    proxy_ip, proxy_port = proxy_machine
    prov_type = provider.type
    appliance.set_proxy('1.1.1.1', proxy_port, prov_type=prov_type)
    request.addfinalizer(lambda: appliance.set_proxy(None, None, prov_type=prov_type))
    validate_provider(provider, valid_proxy=False)


def test_proxy_remove(appliance, proxy_machine, prepare_proxy, provider, request):
    proxy_ip, proxy_port = proxy_machine
    prov_type = provider.type
    appliance.set_proxy(proxy_ip, proxy_port, prov_type=prov_type)
    request.addfinalizer(lambda: appliance.set_proxy(None, None, prov_type=prov_type))
    validate_provider(provider)
    validate_proxy_logs(proxy_ip, appliance.hostname)
    appliance.set_proxy(None, None)
    validate_provider(provider)
    validate_proxy_logs(proxy_ip, appliance.hostname, valid_proxy=False)


def test_proxy_override(appliance, proxy_machine, prepare_proxy, provider, request):
    proxy_ip, proxy_port = proxy_machine
    prov_type = provider.type
    appliance.set_proxy('1.1.1.1', proxy_port, prov_type='default')
    request.addfinalizer(lambda: appliance.set_proxy(None, None, prov_type='default'))
    validate_provider(provider, valid_proxy=False)
    appliance.set_proxy(proxy_ip, proxy_port, prov_type=prov_type)
    request.addfinalizer(lambda: appliance.set_proxy(None, None, prov_type=prov_type))
    validate_provider(provider)
    validate_proxy_logs(proxy_ip, appliance.hostname)
