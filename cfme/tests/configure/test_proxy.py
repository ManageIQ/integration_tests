# -*- coding: utf-8 -*-
import pytest

from cfme.cloud.provider import CloudProvider
from cfme.common.provider import DefaultEndpointForm
from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.providers import get_mgmt
from cfme.utils.ssh import SSHClient
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([CloudProvider], scope='module')
]


@pytest.fixture(scope="module")
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


def validate_provider(provider, valid_proxy=True):
    provider.refresh_provider_relationships()
    wait_for(lambda: provider.last_refresh_error() is None, fail_condition=not valid_proxy,
             fail_func=provider.refresh_provider_relationships, timeout=300, delay=20,
             message='Waiting to provider refresh')
    result = provider.last_refresh_error() is None if valid_proxy else provider.last_refresh_error()
    assert result


def validate_provider_credentials(provider):
    # need to validate credentials after incorrect proxy settings to be able to refresh provider
    view = navigate_to(provider, 'Edit')
    endp_view = provider.create_view(DefaultEndpointForm)
    endp_view.validate.click()

    def _is_error():
        try:
            view.flash.assert_no_error()
        except AssertionError:
            return False
        return True
    wait_for(_is_error,
             fail_func=endp_view.validate.click(), num_sec=100, delay=30,
             message='Waiting for requests from appliance in logs')
    view.cancel.click()


def validate_proxy_logs(proxy_ip, appliance_ip, valid_proxy=True):
    proxy_ssh = SSHClient(hostname=proxy_ip, **conf.credentials['proxy_vm'])
    proxy_ssh.run_command('echo "" > /var/log/squid/access.log')

    def _is_ip_in_log():
        return proxy_ssh.run_command(
            "grep {} /var/log/squid/access.log".format(appliance_ip)).success
    # need to wait until requests will occur in access.log or check if its empty after some time
    wait_for(func=_is_ip_in_log, fail_condition=not valid_proxy, num_sec=300, delay=10,
             message='Waiting for requests from appliance in logs')
    assert _is_ip_in_log() == valid_proxy


@pytest.fixture(scope="function")
def prepare_proxy(proxy_machine):
    proxy_ip, proxy_port = proxy_machine
    proxy_ssh = SSHClient(hostname=proxy_ip, **conf.credentials['proxy_vm'])
    proxy_ssh.run_command('echo "" > /var/log/squid/access.log')
    yield
    proxy_ssh.run_command('echo "" > /var/log/squid/access.log')


@pytest.mark.tier(3)
def test_proxy_valid(appliance, proxy_machine, prepare_proxy, provider, setup_provider, request):
    proxy_ip, proxy_port = proxy_machine
    prov_type = provider.type
    appliance.set_proxy(proxy_ip, proxy_port, prov_type=prov_type)
    request.addfinalizer(lambda: appliance.set_proxy(None, None, prov_type=prov_type))
    validate_provider(provider)
    validate_proxy_logs(proxy_ip, appliance.hostname)


@pytest.mark.tier(3)
def test_proxy_invalid(appliance, proxy_machine, prepare_proxy, setup_provider, provider, request):
    proxy_ip, proxy_port = proxy_machine
    prov_type = provider.type
    appliance.set_proxy('1.1.1.1', proxy_port, prov_type=prov_type)
    request.addfinalizer(lambda: appliance.set_proxy(None, None, prov_type=prov_type))
    request.addfinalizer(lambda: validate_provider_credentials(provider))
    validate_provider(provider, valid_proxy=False)


@pytest.mark.tier(3)
def test_proxy_remove(appliance, proxy_machine, prepare_proxy, provider, setup_provider, request):
    proxy_ip, proxy_port = proxy_machine
    prov_type = provider.type
    appliance.set_proxy(proxy_ip, proxy_port, prov_type=prov_type)
    request.addfinalizer(lambda: appliance.set_proxy(None, None, prov_type=prov_type))
    validate_provider(provider)
    validate_proxy_logs(proxy_ip, appliance.hostname)
    appliance.set_proxy(None, None, prov_type=prov_type)
    validate_provider_credentials(provider)
    validate_provider(provider)
    validate_proxy_logs(proxy_ip, appliance.hostname, valid_proxy=False)


@pytest.mark.tier(3)
def test_proxy_override(appliance, proxy_machine, prepare_proxy, provider, setup_provider, request):
    proxy_ip, proxy_port = proxy_machine
    prov_type = provider.type
    appliance.set_proxy('1.1.1.1', proxy_port, prov_type='default')
    request.addfinalizer(lambda: appliance.set_proxy(None, None, prov_type='default'))
    validate_provider(provider, valid_proxy=False)
    appliance.set_proxy(proxy_ip, proxy_port, prov_type=prov_type)
    request.addfinalizer(lambda: appliance.set_proxy(None, None, prov_type=prov_type))
    validate_provider_credentials(provider)
    validate_provider(provider)
    validate_proxy_logs(proxy_ip, appliance.hostname)
