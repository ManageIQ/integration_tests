import uuid
from copy import copy
from copy import deepcopy

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.common.provider_views import InfraProviderAddView
from cfme.common.provider_views import InfraProvidersDiscoverView
from cfme.common.provider_views import InfraProvidersView
from cfme.fixtures.provider import setup_or_skip
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMEndpoint
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VirtualCenterEndpoint
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.discovery,
    pytest.mark.tier(3),
    pytest.mark.provider([InfraProvider], scope="function"),
]

discovery_ips = [
    {'from': ['10', '120', '120', '120'], 'to': '119',
     'msg': "Infrastructure Providers Discovery returned: "
            "Ending address must be greater than starting address"},
    {'from': ['333', '120', '120', '120'], 'to': '120',
     'msg': "Infrastructure Providers Discovery returned: IP address octets must be 0 to 255"},
    {'from': ['10', '333', '120', '120'], 'to': '120',
     'msg': "Infrastructure Providers Discovery returned: IP address octets must be 0 to 255"},
    {'from': ['10', '120', '333', '120'], 'to': '120',
     'msg': "Infrastructure Providers Discovery returned: IP address octets must be 0 to 255"},
    {'from': ['10', '120', '120', '333'], 'to': '120',
     'msg': "Infrastructure Providers Discovery returned: IP address octets must be 0 to 255"},
    {'from': ['10', '', '', ''], 'to': '120',
     'msg': "Infrastructure Providers Discovery returned: Starting address is malformed"},
    {'from': ['10', '120', '120', '120'], 'to': '',
     'msg': "Infrastructure Providers Discovery returned: Ending address is malformed"}
]


@pytest.mark.sauce
def test_empty_discovery_form_validation_infra(appliance):
    """ Tests that the flash message is correct when discovery form is empty.

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/15h
    """
    collection = appliance.collections.infra_providers
    collection.discover(None)
    view = appliance.browser.create_view(InfraProvidersDiscoverView)
    view.flash.assert_message('At least 1 item must be selected for discovery')


@pytest.mark.sauce
def test_discovery_cancelled_validation_infra(appliance):
    """ Tests that the flash message is correct when discovery is cancelled.

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/15h
    """
    collection = appliance.collections.infra_providers
    collection.discover(None, cancel=True)
    view = appliance.browser.create_view(InfraProvidersView)
    view.flash.assert_success_message('Infrastructure Providers '
                                      'Discovery was cancelled by the user')


@pytest.mark.sauce
def test_add_cancelled_validation_infra(appliance):
    """Tests that the flash message is correct when add is cancelled.

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/15h
    """
    appliance.collections.infra_providers.create(prov_class=VMwareProvider, cancel=True)
    view = appliance.browser.create_view(InfraProvidersView)
    view.flash.assert_success_message('Add of Infrastructure Provider was cancelled by the user')


@pytest.mark.sauce
def test_type_required_validation_infra(appliance):
    """Test to validate type while adding a provider

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/15h
    """
    with pytest.raises(AssertionError):
        appliance.collections.infra_providers.create(prov_class=VMwareProvider)
    view = appliance.browser.create_view(InfraProviderAddView)
    assert not view.add.active


def test_name_required_validation_infra(appliance):
    """Tests to validate the name while adding a provider

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/15h
    """
    collections = appliance.collections.infra_providers
    endpoint = VirtualCenterEndpoint(hostname=fauxfactory.gen_alphanumeric(5))

    with pytest.raises(AssertionError):
        collections.create(prov_class=VMwareProvider, name=None, endpoints=endpoint)

    view = appliance.browser.create_view(InfraProviderAddView)
    assert view.name.help_block == "Required"
    assert not view.add.active


def test_host_name_required_validation_infra(appliance):
    """Test to validate the hostname while adding a provider

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/15h
    """
    endpoint = VirtualCenterEndpoint(hostname=None)
    collections = appliance.collections.infra_providers
    prov = collections.instantiate(prov_class=VMwareProvider, name=fauxfactory.gen_alphanumeric(5),
                                   endpoints=endpoint)

    with pytest.raises(AssertionError):
        prov.create()

    view = appliance.browser.create_view(prov.endpoints_form)
    assert view.hostname.help_block == "Required"
    view = appliance.browser.create_view(InfraProviderAddView)
    assert not view.add.active


def test_name_max_character_validation_infra(request, infra_provider):
    """Test to validate max character for name field

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/15h
    """
    request.addfinalizer(lambda: infra_provider.delete_if_exists(cancel=False))
    name = fauxfactory.gen_alphanumeric(255)
    with update(infra_provider):
        infra_provider.name = name
    assert infra_provider.exists


def test_host_name_max_character_validation_infra(appliance):
    """Test to validate max character for host name field

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/10h
    """
    endpoint = VirtualCenterEndpoint(hostname=fauxfactory.gen_alphanumeric(256))
    collections = appliance.collections.infra_providers
    prov = collections.instantiate(prov_class=VMwareProvider,
                                   name=fauxfactory.gen_alphanumeric(5),
                                   endpoints=endpoint)
    try:
        prov.create()
    except AssertionError:
        view = appliance.browser.create_view(prov.endpoints_form)
        assert view.hostname.value == prov.hostname[0:255]


def test_api_port_max_character_validation_infra(appliance):
    """Test to validate max character for api port field

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/15h
    """
    collections = appliance.collections.infra_providers
    endpoint = RHEVMEndpoint(hostname=fauxfactory.gen_alphanumeric(5),
                             api_port=fauxfactory.gen_alphanumeric(16),
                             verify_tls=None,
                             ca_certs=None)
    prov = collections.instantiate(prov_class=RHEVMProvider,
                                   name=fauxfactory.gen_alphanumeric(5),
                                   endpoints=endpoint)
    try:
        prov.create()
    except AssertionError:
        view = appliance.browser.create_view(prov.endpoints_form)
        text = view.default.api_port.value
        assert text == prov.default_endpoint.api_port[0:15]


@pytest.mark.tier(1)
def test_providers_discovery(request, appliance, has_no_providers, provider):
    """Tests provider discovery

    Metadata:
        test_flag: crud

    Bugzilla:
        1559796

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/8h
    """
    appliance.collections.infra_providers.discover(provider, cancel=False,
                                                   start_ip=provider.start_ip,
                                                   end_ip=provider.end_ip)
    view = provider.browser.create_view(InfraProvidersView)
    view.flash.assert_success_message('Infrastructure Providers: Discovery successfully initiated')

    request.addfinalizer(InfraProvider.clear_providers)
    appliance.collections.infra_providers.wait_for_a_provider()


def test_infra_provider_add_with_bad_credentials(has_no_providers, provider):
    """Tests provider add with bad credentials

    Metadata:
        test_flag: crud

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/8h
    """
    provider.default_endpoint.credentials = Credential(
        principal='bad',
        secret='reallybad',
        verify_secret='reallybad'
    )

    with pytest.raises(AssertionError, match=provider.bad_credentials_error_msg):
        provider.create(validate_credentials=True)


@pytest.mark.tier(1)
@pytest.mark.smoke
def test_infra_provider_crud(provider, has_no_providers):
    """Tests provider add with good credentials

    Metadata:
        test_flag: crud

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/5h
    """
    provider.create()
    # Fails on upstream, all provider types - BZ1087476
    provider.validate_stats(ui=True)

    old_name = provider.name
    with update(provider):
        provider.name = str(uuid.uuid4())  # random uuid

    with update(provider):
        provider.name = old_name  # old name

    provider.delete()
    provider.wait_for_delete()


@pytest.mark.tier(1)
@pytest.mark.parametrize('verify_tls', [False, True], ids=['no_tls', 'tls'])
@pytest.mark.provider([RHEVMProvider])
def test_provider_rhv_create_delete_tls(request, has_no_providers, provider, verify_tls):
    """Tests RHV provider creation with and without TLS encryption

    Metadata:
       test_flag: crud

    Polarion:
        assignee: pvala
        casecomponent: Infra
        initialEstimate: 1/4h
    """

    if not provider.endpoints.get('default').__dict__.get('verify_tls'):
        pytest.skip("test requires RHV providers with verify_tls set")

    prov = copy(provider)
    request.addfinalizer(lambda: prov.delete_if_exists(cancel=False))

    if not verify_tls:
        endpoints = deepcopy(prov.endpoints)
        endpoints['default'].verify_tls = False
        endpoints['default'].ca_certs = None

        prov.endpoints = endpoints
        prov.name = f"{provider.name}-no-tls"

    prov.create()
    prov.validate_stats(ui=True)

    prov.delete()
    prov.wait_for_delete()


DEVICES_COUNT_TOLERANCE = 5
""" The difference of guest devices counts between provider refresh we do allow. """


@test_requirements.rhev
@pytest.mark.meta(automates=[1691109, 1731237])
@pytest.mark.provider([RHEVMProvider], selector=ONE_PER_VERSION, scope="function")
def test_rhv_guest_devices_count(appliance, setup_provider, provider):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/6h
        testSteps:
            1. Check GuestDevice.count in a rails console
            2. Refresh RHV provider
            3. Check GuestDevice.count again
        expectedResults:
            1.
            2.
            3. The count is the same as in step 1
    Bugzilla:
        1691109
        1731237
    """
    def _gd_count():  # find the Guest Device count in the output
        command = "GuestDevice.count"
        gd_count_command = appliance.ssh_client.run_rails_console(command).output
        return int(gd_count_command[gd_count_command.find(command) + len(command):])

    def _refresh_provider():
        provider.refresh_provider_relationships()
        # takes a bit more time to update Guest Devices initially
        return provider.is_refreshed() and _gd_count() != 0

    gd_count_before = _gd_count()

    wait_for(_refresh_provider, timeout=300, delay=30)
    gd_count_after = _gd_count()
    assert abs(gd_count_after - gd_count_before) < DEVICES_COUNT_TOLERANCE, \
        "The guest devices count changed suspiciously after refresh!"


@test_requirements.rhev
@pytest.mark.meta(automates=[1594817])
@pytest.mark.provider([RHEVMProvider], selector=ONE, scope="function")
def test_rhv_custom_attributes_after_refresh(appliance, setup_provider, provider):
    """
    Bugzilla:
        1594817

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/8h
        testSteps:
            1. Create a custom attribute on a vm
            2. Run a targeted refresh of the VM
            3. Check if the custom attribute is still there
        expectedResults:
            1.
            2.
            3. The custom attribute is still there
    """
    # get the name of any VM on the provider
    view = navigate_to(provider, 'ProviderVms')
    vm_name = view.entities.all_entity_names[0]

    vm = f"Vm.where(name: '{vm_name}').last"

    # set the attributes to the VM
    assert appliance.ssh_client.run_rails_console(f"{vm}.miq_custom_set('mykey', 'myval')").success

    # check the attributes are set
    assert "myval" in appliance.ssh_client.run_rails_console(f"{vm}.miq_custom_get('mykey')").output

    # run a targeted refresh on the VM
    assert appliance.ssh_client.run_rails_console(f"EmsRefresh.refresh({vm})").success

    # verify the attribute is still here
    assert "myval" in appliance.ssh_client.run_rails_console(f"{vm}.miq_custom_get('mykey')").output


@test_requirements.general_ui
def test_infrastructure_add_provider_trailing_whitespaces(appliance):
    """Test to validate the hostname and username should be without whitespaces

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/8h
    """
    collections = appliance.collections.infra_providers
    credentials = Credential(principal="test test", secret=fauxfactory.gen_alphanumeric(5))
    endpoint = VirtualCenterEndpoint(hostname="test test", credentials=credentials)
    prov = collections.instantiate(prov_class=VMwareProvider,
                                   name=fauxfactory.gen_alphanumeric(5),
                                   endpoints=endpoint)
    with pytest.raises(AssertionError):
        prov.create()
    view = appliance.browser.create_view(prov.endpoints_form)
    assert view.hostname.help_block == "Spaces are prohibited"
    assert view.username.help_block == "Spaces are prohibited"
    view = appliance.browser.create_view(InfraProviderAddView)
    assert not view.add.active


def test_infra_discovery_screen(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/6h
    """
    collections = appliance.collections.infra_providers
    view = navigate_to(collections, 'Discover')
    assert view.is_displayed
    assert view.vmware.is_displayed
    assert view.scvmm.is_displayed
    assert view.rhevm.is_displayed

    view.vmware.click()
    assert view.vmware.selected
    view.vmware.click()
    assert not view.vmware.selected

    view.scvmm.click()
    assert view.scvmm.selected
    view.scvmm.click()
    assert not view.scvmm.selected

    view.rhevm.click()
    assert view.rhevm.selected
    view.rhevm.click()
    assert not view.rhevm.selected

    assert view.osp_infra.is_displayed
    view.osp_infra.click()
    assert view.osp_infra.selected
    view.osp_infra.click()
    assert not view.osp_infra.selected

    view.start.click()
    view.flash.assert_message("At least 1 item must be selected for discovery")

    view.vmware.click()
    for ips in discovery_ips:
        from_ips = ips['from']
        view.fill({"from_ip1": from_ips[0],
                   "from_ip2": from_ips[1],
                   "from_ip3": from_ips[2],
                   "from_ip4": from_ips[3],
                   "to_ip4": ips['to']})
        view.start.click()
        view.flash.assert_message(ips['msg'])


@pytest.fixture
def setup_provider_min_templates(request, appliance, provider, min_templates):
    if len(provider.mgmt.list_templates()) < min_templates:
        pytest.skip(f'Number of templates on {provider} does not meet minimum '
                    f'for test parameter {min_templates}, skipping and not setting up provider')
    # Function-scoped fixture to set up a provider
    setup_or_skip(request, provider)


@pytest.mark.provider([InfraProvider], selector=ONE, scope="function")
@pytest.mark.parametrize("min_templates", [2, 4])
@pytest.mark.parametrize("templates_collection", ["provider", "appliance"])
@pytest.mark.meta(automates=[1784180, 1794434, 1746449])
def test_compare_templates(appliance, setup_provider_min_templates, provider, min_templates,
                           templates_collection):
    """
    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/6h
    Bugzilla:
        1746449
        1784180
        1794434
    """
    t_coll = locals()[templates_collection].collections.infra_templates.all()[:min_templates]
    compare_view = locals()[templates_collection].collections.infra_templates.compare_entities(
        entities_list=t_coll)
    assert compare_view.is_displayed

    t_list = [t.name for t in t_coll]
    assert compare_view.verify_checked_items_compared(t_list, compare_view)
