import pytest

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([AzureProvider, GCEProvider, EC2Provider], scope='module'),
    pytest.mark.usefixtures('setup_provider_modscope'),
    test_requirements.appliance
]


@pytest.fixture(scope='module')
def proxy_data(utility_vm):
    utility_vm_ip, __, data = utility_vm
    yield utility_vm_ip, data.proxy.port


@pytest.fixture(scope='module')
def proxy_ssh(utility_vm):
    proxy_ip, injected_user_cred, __ = utility_vm
    with SSHClient(
            hostname=proxy_ip,
            username=injected_user_cred.principal,
            password=injected_user_cred.secret) as ssh_client:
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
def prepare_proxy_specific(proxy_ssh, provider, appliance, proxy_data):
    proxy_ip, proxy_port = proxy_data
    prov_type = provider.type
    # 192.0.2.1 is from TEST-NET-1 which doesn't exist on the internet (RFC5737).
    appliance.set_proxy('192.0.2.1', proxy_port, prov_type='default')
    appliance.set_proxy(proxy_ip, proxy_port, prov_type=prov_type)
    proxy_ssh.run_command('echo "" > /var/log/squid/access.log')
    yield
    appliance.reset_proxy(prov_type)
    appliance.reset_proxy()


@pytest.fixture(scope="function")
def prepare_proxy_default(proxy_ssh, provider, appliance, proxy_data):
    proxy_ip, proxy_port = proxy_data
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


def test_proxy_valid(appliance, proxy_ssh, prepare_proxy_default, provider):
    """ Check whether valid proxy settings works.

    Bugzilla:
        1623862

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Appliance
        testSteps:
            1. Configure appliance to use proxy for default provider.
            2. Configure appliance to use not use proxy for specific provider.
            3. Chceck whether the provider is accessed trough proxy by chceking the proxy logs.
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


def test_proxy_override(appliance, proxy_ssh, prepare_proxy_specific, provider):
    """ Check whether invalid default and valid specific provider proxy settings
    results in provider refresh working.

    Bugzilla:
        1623862

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        initialEstimate: 1/4h
        testSteps:
            1. Configure default proxy to invalid entry.
            2. Configure specific proxy to valid entry.
            3. Check whether the provider is accessed trough proxy by checking the proxy logs.
            4. Wait for the provider refresh to complete to check the settings worked.
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

    Bugzilla:
        1623550

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Appliance
        testSteps:
            1. Configure default proxy to invalid entry.
            2. Configure specific proxy to invalid entry.
            3. Wait for the provider refresh to complete to check the settings causes error.
    """
    provider.refresh_provider_relationships()
    view = navigate_to(provider, 'Details')
    view.toolbar.view_selector.select('Summary View')

    def last_refresh_failed():
        view.toolbar.reload.click()
        refresh_failed_msg = ('execution expired' if provider.one_of(EC2Provider) else
                              'Timed out connecting to server')
        return refresh_failed_msg in (
            view.entities.summary('Status').get_text_of('Last Refresh'))

    wait_for(last_refresh_failed,
             fail_condition=False,
             num_sec=240,
             delay=20,
             fail_func=provider.refresh_provider_relationships
             )


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_remove_default():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the default proxy settings.  For this test you want to create
    an default proxy, verified it worked, and then remove the proxy and
    verify it didn"t use a proxy
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: jhenner
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/8h
        setup: I think the best way to do this one is start with a bad proxy value,
               get the connection error, and then remove the proxy values and make
               sure it starts connecting again.  I"ll have to see if there is a log
               value we can look at.  Otherwise, you need to shutdown the proxy
               server to be absolutely sure.
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_remove_azure():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the azure proxy settings.  For this test you want to create an
    azure proxy, verified it worked, and then remove the proxy and verify
    it used the default which may or may not be blank.
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: jhenner
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/8h
        setup: I think the best way to do this one is start with a bad proxy value,
               get the connection error, and then remove the proxy values and make
               sure it starts connecting again.  I"ll have to see if there is a log
               value we can look at.  Otherwise, you need to shutdown the proxy
               server to be absolutely sure.
        startsin: 5.7
        upstream: yes
    """
    pass
