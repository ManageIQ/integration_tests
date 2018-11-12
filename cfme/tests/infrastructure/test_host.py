# -*- coding: utf-8 -*-
import pytest
import random
import socket

from cfme.base.credential import Credential
from cfme.common.host_views import HostsEditView
from cfme.common.provider_views import ProviderNodesView
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([InfraProvider], required_fields=['hosts'], scope='module'),
]

VIEWS = ('Grid View', 'Tile View', 'List View')


@pytest.fixture(scope='module')
def host_ips(provider):
    """Returns tuple of hosts' IP addresses."""
    ipaddresses = []

    all_hosts = provider.data.get('hosts', [])
    for host in all_hosts:
        ipaddr = None
        if hasattr(host, 'ipaddress'):
            ipaddr = host.ipaddress
        if not ipaddr:
            try:
                ipaddr = socket.gethostbyname(host.name)
            except Exception:
                pass
        if ipaddr:
            ipaddresses.append(ipaddr)
    if not ipaddresses:
        pytest.skip('No hosts IP addresses found for provider "{}"'.format(provider.name))

    ipaddresses.sort()
    return tuple(ipaddresses)


@pytest.fixture(scope='module')
def create_250_hosts(appliance):
    script_downloaded = appliance.ssh_client.run_command(
        "wget -P /var/www/miq/vmdb/ "
        "https://gist.githubusercontent.com/NickLaMuro/225833358423723ed17ff294415fa6b4/raw/"
        "f717ccb83f530f653aabe67fe9389164513ef90d/bz_1580569_db_replication_script.rb")
    assert script_downloaded.success, script_downloaded.output

    create_250_hosts = appliance.ssh_client.run_command(
        "cd /var/www/miq/vmdb && bin/rails r bz_1580569_db_replication_script.rb")
    assert create_250_hosts.success
    yield

    appliance.ssh_client.run_command("rm -f /var/www/miq/vmdb/bz_1580569_db_replication_script.rb")
    appliance.ssh_client.run_rails_console("[Host].each(&:delete_all)")
    appliance.delete_all_providers()


def navigate_and_select_quads(provider):
    """navigate to the hosts edit page and select all the quads on the first page

    Returns:
        view: the provider nodes view, quadicons already selected"""
    hosts_view = navigate_to(provider, 'ProviderNodes')
    assert hosts_view.is_displayed
    [h.check() for h in hosts_view.entities.get_all()]

    hosts_view.toolbar.configuration.item_select('Edit Selected items')
    edit_view = provider.create_view(HostsEditView)
    assert edit_view.is_displayed
    return edit_view


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider))
def test_discover_host(request, provider, appliance, host_ips):
    """Tests hosts discovery."""
    if provider.delete_if_exists(cancel=False):
        provider.wait_for_delete()

    collection = appliance.collections.hosts

    def _cleanup():
        all_hosts = collection.all()
        if all_hosts:
            collection.delete(*all_hosts)

    _cleanup()
    request.addfinalizer(_cleanup)

    collection.discover(host_ips[0], host_ips[-1], esx=True)
    hosts_view = navigate_to(collection, 'All')
    expected_len = len(provider.data.get('hosts', {}))

    def _check_items_visibility():
        hosts_view.browser.refresh()
        return len(hosts_view.entities.entity_names) == expected_len

    wait_for(_check_items_visibility, num_sec=600, delay=10)
    for host in hosts_view.entities.entity_names:
        assert host in host_ips


@pytest.mark.rhv2
# Tests to automate BZ 1201092
@pytest.mark.meta(blockers=[BZ(1619626, forced_streams=['5.9', '5.10'],
                               unblock=lambda provider: not provider.one_of(RHEVMProvider))])
@pytest.mark.parametrize("creds", ["default", "remote_login", "web_services"],
                         ids=["default", "remote", "web"])
@pytest.mark.uncollectif(
    lambda provider, creds:
        creds in ['remote_login', 'web_services'] and provider.one_of(RHEVMProvider),
    reason="Not relevant for RHEVM Provider."
)
def test_multiple_host_good_creds(setup_provider, provider, creds):
    if len(provider.data.get('hosts', {})) < 2:
        pytest.skip('not enough hosts to run test')
    """  Tests multiple host credentialing  with good credentials """
    host = random.choice(provider.data["hosts"])
    host_creds = credentials[host['credentials'][creds]]
    cred = Credential(principal=host_creds.username, secret=host_creds.password)

    edit_view = navigate_and_select_quads(provider=provider)

    # Fill form with valid credentials for default endpoint and validate
    edit_view.endpoints.default.fill_with(cred.view_value_mapping)
    edit_view.validation_host.fill(host.name)
    edit_view.endpoints.default.validate_button.click()

    edit_view.flash.assert_no_error()
    edit_view.flash.assert_success_message('Credential validation was successful')

    # Save changes
    edit_view.save_button.click()
    view = provider.create_view(ProviderNodesView)
    view.flash.assert_no_error()
    view.flash.assert_success_message('Credentials/Settings saved successfully')


@pytest.mark.rhv3
@pytest.mark.meta(blockers=[BZ(1619626, forced_streams=['5.9', '5.10'],
                               unblock=lambda provider: not provider.one_of(RHEVMProvider))])
def test_multiple_host_bad_creds(setup_provider, provider):
    """    Tests multiple host credentialing with bad credentials """
    if len(provider.data.get('hosts', {})) < 2:
        pytest.skip('not enough hosts to run test')

    host = random.choice(provider.data["hosts"])
    cred = Credential(principal='wrong', secret='bad_password')

    edit_view = navigate_and_select_quads(provider=provider)

    edit_view.endpoints.default.fill_with(cred.view_value_mapping)
    edit_view.validation_host.fill(host.name)
    edit_view.endpoints.default.validate_button.click()

    if provider.one_of(RHEVMProvider):
        msg = 'Login failed due to a bad username or password.'
    elif provider.one_of(SCVMMProvider):
        msg = 'Check credentials. Remote error message: WinRM::WinRMAuthorizationError'
    else:
        msg = 'Cannot complete login due to an incorrect user name or password.'
    edit_view.flash.assert_message(msg)

    edit_view.cancel_button.click()


@pytest.mark.meta(blockers=[BZ(1648658, forced_streams=["5.9"])])
@pytest.mark.provider([InfraProvider], override=True, selector=ONE, scope='module')
def test_tag_host_after_provider_delete(provider, appliance, setup_provider, request):
    """Test if host can be tagged after delete"""
    host_on_provider = provider.hosts.all()[0]
    provider.delete(cancel=False)
    provider.wait_for_delete()
    all_hosts = appliance.collections.hosts.all()
    # need to find the host without the link to the provider,
    # so the navigation goes Compute -> Infrastructure -> Hosts, not Providers
    for host in all_hosts:
        if host.name == host_on_provider.name:
            host_to_tag = host
            break
    try:
        tag = host_to_tag.add_tag()
    except NameError:
        raise pytest.fail("Host not found!")
    request.addfinalizer(lambda: host.remove_tag(tag))


@pytest.mark.parametrize('view_type', VIEWS)
def test_250_vmware_hosts_loading(appliance, create_250_hosts, view_type):
    """
    Test to automate BZ1580569
    """
    # Without the patch, this will cause the process to consume roughly 10+ Gigs of RAM
    # due to a poorly optimized database query
    rails_console = appliance.ssh_client.run_rails_console(
        "MiqReport.load_from_view_options(Host, User.where(:userid => 'admin').first)"
        ".paged_view_search", timeout=60
    )
    assert rails_console.success

    # Check it loads fast in the UI
    view = navigate_to(appliance.collections.hosts, 'All')
    view.entities.paginator.set_items_per_page(1000)
    view.toolbar.view_selector.select(view_type)
    wait_for(view.entities.get_first_entity, timeout=60, message='Wait for the view')
