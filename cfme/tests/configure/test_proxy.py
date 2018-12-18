# -*- coding: utf-8 -*-
import pytest
import os.path
from textwrap import dedent

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.providers import get_mgmt
from cfme.utils.ssh import SSHClient
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([AzureProvider, GCEProvider], scope='module'),
    pytest.mark.usefixtures('setup_provider_modscope')
]


@pytest.fixture(scope='module')
def proxy_machine():
    """ Deploy vm for proxy test

    This fixture uses for deploy vm on provider from yaml and then receive it's ip
    After test run vm deletes from provider
    """
    depot_machine_name = random_vm_name('proxy')
    data = conf.cfme_data.get("utility_vm")
    proxy_provider_key = data["provider"]
    proxy_template_name = data["template_name"]
    proxy_port = '3128'
    prov = get_mgmt(proxy_provider_key)
    vm = deploy_template(proxy_provider_key,
                         depot_machine_name,
                         template_name=proxy_template_name)
    wait_for(func=lambda: vm.ip is not None, num_sec=300, delay=10,
             message='Waiting for instance "{}" ip to be present.'.format(vm.name))

    credentials_key = conf.cfme_data['utility_vm']['credentials']
    with SSHClient(
            hostname=vm.ip,
            **conf.credentials[credentials_key]) as ssh_client:
        repofile = os.path.join(os.path.dirname(__file__), 'rhel.repo')
        ssh_client.run_command(dedent('''\
            cat > /etc/yum.repos.d/rhel.repo <<EOF
            [rhel]
            name=RHEL 7.5-Update
            baseurl={baseurl}
            enabled=1
            gpgcheck=0
            skip_if_unavailable=False
            EOF
            ''').format(baseurl=conf.cfme_data['basic_info']['rhel7_updates_url']))
        for line in ('yum install -y squid && systemctl start squid',
                     'firewall-cmd --zone=public --add-port=3128/tcp --permanent',
                     'firewall-cmd --reload'):
            assert ssh_client.run_command(line).success

    yield vm.ip, proxy_port
    vm.delete()


@pytest.fixture(scope='module')
def proxy_ssh(proxy_machine):
    proxy_ip, __ = proxy_machine
    credentials_key = conf.cfme_data['utility_vm']['credentials']
    with SSHClient(
            hostname=proxy_ip,
            **conf.credentials[credentials_key]) as ssh_client:
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
def prepare_proxy_specific(proxy_ssh, provider, appliance, proxy_machine):
    proxy_ip, proxy_port = proxy_machine
    prov_type = provider.type
    # 192.0.2.1 is from TEST-NET-1 which doesn't exist on the internet (RFC5737).
    appliance.set_proxy('192.0.2.1', proxy_port, prov_type='default')
    appliance.set_proxy(proxy_ip, proxy_port, prov_type=prov_type)
    proxy_ssh.run_command('echo "" > /var/log/squid/access.log')
    yield
    appliance.reset_proxy(prov_type)
    appliance.reset_proxy()


@pytest.fixture(scope="function")
def prepare_proxy_default(proxy_ssh, provider, appliance, proxy_machine):
    proxy_ip, proxy_port = proxy_machine
    prov_type = provider.type
    appliance.set_proxy(proxy_ip, proxy_port, prov_type='default')
    appliance.reset_proxy(prov_type)
    proxy_ssh.run_command('echo "" > /var/log/squid/access.log')
    yield
    appliance.reset_proxy()
    appliance.reset_proxy(prov_type)


@pytest.fixture(scope="function")
def prepare_proxy_invalid(provider, appliance):
    prov_type = provider.type
    # 192.0.2.1 is from TEST-NET-1 which doesn't exist on the internet (RFC5737).
    appliance.set_proxy('192.0.2.1', '1234', prov_type='default')
    appliance.set_proxy('192.0.2.1', '1234', prov_type=prov_type)
    yield
    appliance.reset_proxy(prov_type)
    appliance.reset_proxy()


@pytest.mark.meta(blockers=[
    BZ(1623862, forced_streams=['5.9', '5.10'],
       unblock=lambda provider: provider.one_of(AzureProvider))])
def test_proxy_valid(appliance, proxy_machine, proxy_ssh, prepare_proxy_default, provider):
    """ Check whether valid proxy settings works.

    Steps:
     * Configure appliance to use proxy for default provider.
     * Configure appliance to use not use proxy for specific provider.
     * Chceck whether the provider is accessed trough proxy by chceking the
       proxy logs.

    Polarion:
        assignee: None
        initialEstimate: None
    """
    provider.refresh_provider_relationships()
    validate_proxy_logs(provider, proxy_ssh, appliance.hostname)
    wait_for(
        provider.is_refreshed,
        func_kwargs={"refresh_delta": 120},
        fail_condition=True,
        num_sec=300,
        delay=30
    )


@pytest.mark.meta(blockers=[
    BZ(1623862, forced_streams=['5.9', '5.10'],
       unblock=lambda provider: provider.one_of(AzureProvider))])
def test_proxy_override(appliance, proxy_ssh, prepare_proxy_specific, provider):
    """ Check whether invalid default and valid specific provider proxy settings
    results in provider refresh working.

    Steps:
     * Configure default proxy to invalid entry.
     * Configure specific proxy to valid entry.
     * Check whether the provider is accessed trough proxy by checking the proxy logs.
     * Wait for the provider refresh to complete to check the settings worked.

    Polarion:
        assignee: None
        initialEstimate: None
    """
    provider.refresh_provider_relationships()
    validate_proxy_logs(provider, proxy_ssh, appliance.hostname)
    wait_for(
        provider.is_refreshed,
        func_kwargs={"refresh_delta": 120},
        fail_condition=True,
        num_sec=300,
        delay=30
    )


def test_proxy_invalid(appliance, prepare_proxy_invalid, provider):
    """ Check whether invalid default and invalid specific provider proxy settings
     results in provider refresh not working.

    Steps:
     * Configure default proxy to invalid entry.
     * Configure specific proxy to invalid entry.
     * Wait for the provider refresh to complete to check the settings causes error.

    Polarion:
        assignee: None
        initialEstimate: None
    """
    provider.refresh_provider_relationships()

    view = navigate_to(provider, 'Details')

    if appliance.version >= '5.10':
        view.toolbar.view_selector.select('Summary View')

    def last_refresh_failed():
        view.toolbar.reload.click()
        status = view.entities.summary('Status').get_text_of('Last Refresh')
        return any(('Timed out connecting to server' in status,
                   'execution expired' in status))

    wait_for(last_refresh_failed, fail_condition=False, num_sec=240, delay=5)
