# -*- coding: utf-8 -*-
import random
import socket

import pytest
from wait_for import TimedOutError

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.common.host_views import HostsEditView
from cfme.common.host_views import HostsCompareView
from cfme.common.provider_views import InfraProviderDetailsView
from cfme.common.provider_views import ProviderNodesView
from cfme.fixtures.provider import setup_or_skip
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.tests.networks.test_sdn_downloads import handle_extra_tabs
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([InfraProvider],
                         required_fields=['hosts'], scope='module',
                         selector=ONE_PER_TYPE),
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


@pytest.mark.provider([VMwareProvider],
                      required_fields=['hosts'],
                      selector=ONE_PER_VERSION,
                      override=True)
def test_discover_host(request, provider, appliance, host_ips):
    """Tests hosts discovery.

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: Infra
    """
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
@pytest.mark.parametrize("creds", ["default", "remote_login", "web_services"],
                         ids=["default", "remote", "web"])
@pytest.mark.uncollectif(
    lambda provider, creds:
        creds in ['remote_login', 'web_services'] and provider.one_of(RHEVMProvider),
    reason="cred type not relevant for RHEVM Provider."
)
def test_multiple_host_good_creds(setup_provider, provider, creds):
    """

    Bugzilla:
        1619626
        1201092

    Polarion:
        assignee: nachandr
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    if len(provider.data.get('hosts', {})) < 2:
        pytest.skip('not enough hosts to run test')
    """  Tests multiple host credentialing  with good credentials """
    host = random.choice(provider.data["hosts"])
    host_creds = credentials.get(host['credentials'].get(creds, None), None)
    if not host_creds:
        pytest.skip("This host {} doesn't have necessary creds {}. skipping test. "
                    "Please check yaml data".format(host, creds))
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
def test_multiple_host_bad_creds(setup_provider, provider):
    """    Tests multiple host credentialing with bad credentials

    Polarion:
        assignee: nachandr
        caseimportance: medium
        casecomponent: Infra
        initialEstimate: 1/15h
    """
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


@test_requirements.tag
@pytest.mark.provider([InfraProvider], override=True, selector=ONE, scope='module')
def test_tag_host_after_provider_delete(provider, appliance, setup_provider, request):
    """Test if host can be tagged after delete

    Polarion:
        assignee: anikifor
        initialEstimate: 1/8h
        casecomponent: Tagging
    """
    host_on_provider = provider.hosts.all()[0]
    provider.delete()
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


@test_requirements.general_ui
@pytest.mark.parametrize('view_type', VIEWS)
def test_250_vmware_hosts_loading(appliance, create_250_hosts, view_type):
    """
    Test to automate BZ1580569

    Polarion:
        assignee: pvala
        initialEstimate: 1/4h
        casecomponent: WebUI
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


@test_requirements.general_ui
@pytest.mark.parametrize(
    "power_state", ["preparing_for_maintenance", "maintenance", "unknown", "off", "on"]
)
def test_infrastructure_hosts_icons_states(
    appliance, request, power_state, setup_provider, provider, soft_assert
):
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/3h
        setup:
            1. Add a RHEVM provider.
            2. SSH into appliance console and run `psql vmdb_production`
        testSteps:
            1. Check if the Quadicon(Host's ALL page)
                and host(Host's Detail page) power_state changes after running the command:
                `UPDATE hosts SET power_state = ':power_state' WHERE name=':host_name';`
    """
    # get host and host details
    host = provider.hosts.all()[0]
    host_name = host.name
    reset_state = host.rest_api_entity.power_state
    hosts = appliance.db.client["hosts"]

    # change host power_state
    result = (
        appliance.db.client.session.query(hosts)
        .filter(hosts.name == host_name)
        .update({hosts.power_state: power_state})
    )
    assert result == 1

    # reset host power_state
    @request.addfinalizer
    def _finalize():
        appliance.db.client.session.query(hosts).filter(hosts.name == host_name).update(
            {hosts.power_state: reset_state}
        )

    # assert power_state from quadicon
    view = navigate_to(appliance.collections.hosts, "All")
    host_entity = view.entities.get_entity(name=host_name)
    actual_state = host_entity.data["quad"]["topRight"]["tooltip"]
    soft_assert(
        actual_state == power_state,
        "Power state in the quadicon[{}] did not match with {}.".format(
            actual_state, power_state
        ),
    )

    # assert power_state from Details page
    view = navigate_to(host, "Details")
    actual_state = view.entities.summary("Properties").get_text_of("Power State")
    soft_assert(
        actual_state == power_state,
        "Power state in the summary table[{}] did not match with [{}].".format(
            actual_state, power_state
        ),
    )


@test_requirements.rhev
@pytest.mark.rhv3
@pytest.mark.provider([RHEVMProvider], required_fields=['hosts'], override=True, selector=ONE)
@pytest.mark.meta(automates=[1528859])
def test_hosts_not_displayed_several_times(appliance, provider, setup_provider):
    """Tests hosts not displayed several times after removing and adding provider.

        Polarion:
            assignee: anikifor
            initialEstimate: 1/20h
            casecomponent: Infra
        """
    host_count = navigate_to(appliance.collections.hosts, "All").paginator.items_amount
    provider.delete(cancel=False)
    provider.wait_for_delete()
    provider.create()
    assert host_count == navigate_to(appliance.collections.hosts, "All").paginator.items_amount


@pytest.fixture
def setup_provider_min_hosts(request, provider, min_hosts=2):
    num_hosts = len(provider.data.get('hosts', {}))
    if num_hosts < min_hosts:
        pytest.skip(f'Not enough hosts({num_hosts}) to run test. Need at least {min_hosts}')
    # Function-scoped fixture to set up a provider
    return setup_or_skip(request, provider)


@test_requirements.infra_hosts
def test_infrastructure_hosts_refresh_multi(appliance, setup_provider_min_hosts, provider):
    """
    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/6h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Providers view.
            2. Click on a provider quadicon, and then the hosts link along the top row of the view.
            3. Select all hosts (need at least 2 hosts) by checking the box in upper left of
               quadicons.
            4. Click "Refresh Relationships and Power States" under the Configuration
               dropdowm, and then click "OK" when prompted.
        expectedResults:
            1. Providers view is displayed.
            2. Hosts view is displayed.
            3.
            4. "Refresh initiated for X Hosts from the CFME Database" is displayed in green
               banner where "X" is the number of selected hosts. Properties for each host are
               refreshed. Making changes to test pre-commithooks
    """
    num_refresh = 2
    my_slice = slice(0, num_refresh, None)
    hosts_view = navigate_to(provider.collections.hosts, "All")
    num_hosts = hosts_view.entities.paginator.items_amount
    if num_hosts < num_refresh:
        pytest.skip('not enough hosts in appliance UI to run test')
    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=[f"'Refresh Provider' successfully initiated for "
                                              f"{num_refresh} Hosts"],
                            hostname=appliance.hostname)
    evm_tail.start_monitoring()
    for h in hosts_view.entities.get_all(slice=my_slice):
        h.check()
    hosts_view.toolbar.configuration.item_select('Refresh Relationships and Power States',
                                                 handle_alert=True)
    hosts_view.flash.assert_success_message(
        f'Refresh initiated for {num_refresh} Hosts from the CFME Database'
    )
    try:
        wait_for(provider.is_refreshed, func_kwargs={'force_refresh': False}, num_sec=300,
                 delay=10)
    except TimedOutError:
        pytest.fail("Hosts were not refreshed within given time")
    assert evm_tail.validate(wait="30s")


@test_requirements.infra_hosts
@pytest.mark.meta(blockers=[BZ(1738664, forced_streams=["5.10"])], automates=[1738664])
@pytest.mark.parametrize("hosts_collection", ["provider", "appliance"])
@pytest.mark.parametrize(
    "report_format", ["Download as Text", "Download as CSV", "Print or export as PDF"],
    ids=["txt", "csv", "pdf"]
)
def test_infrastructure_hosts_navigation_after_download(
    appliance, setup_provider, provider, report_format, hosts_collection
):
    """
    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/3h
    Bugzilla:
        1738664

    """
    if hosts_collection == "provider":
        hosts_view = navigate_to(provider.collections.hosts, "All")
    elif hosts_collection == "appliance":
        hosts_view = navigate_to(appliance.collections.hosts, "All")
    hosts_view.toolbar.download.item_select(report_format)
    if report_format == "Print or export as PDF":
        handle_extra_tabs(hosts_view)
    hosts_view.navigation.select("Compute")
    if hosts_collection == "provider":
        provider_view = provider.create_view(InfraProviderDetailsView)
        assert provider_view.is_displayed
    elif hosts_collection == "appliance":
        assert hosts_view.is_displayed


@test_requirements.infra_hosts
@pytest.mark.meta(blockers=[BZ(1746214, forced_streams=["5.10"])], automates=[1746214])
def test_compare_hosts_from_provider_allhosts(appliance, setup_provider_min_hosts, provider):
    """
    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/6h
    Bugzilla:
        1746214

    """
    hosts_view = navigate_to(provider.collections.hosts, "All")
    num_hosts = len(hosts_view.entities.get_all())
    if num_hosts < 2:
        pytest.skip('not enough hosts in appliance UI to run test')
    for h in hosts_view.entities.get_all():
        h.check()
    hosts_view.toolbar.configuration.item_select('Compare Selected items',
                                                 handle_alert=True)
    compare_hosts_view = provider.create_view(HostsCompareView)
    assert compare_hosts_view.is_displayed
