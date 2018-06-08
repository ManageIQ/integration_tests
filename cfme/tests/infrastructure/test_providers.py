# -*- coding: utf-8 -*-
import uuid
from copy import copy, deepcopy

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.common.provider_views import (InfraProviderAddView,
                                        InfraProvidersView,
                                        InfraProvidersDiscoverView)
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider, RHEVMEndpoint
from cfme.infrastructure.provider.virtualcenter import VMwareProvider, VirtualCenterEndpoint
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.update import update

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
    """ Tests that the flash message is correct when discovery form is empty."""
    collection = appliance.collections.infra_providers
    collection.discover(None)
    view = appliance.browser.create_view(InfraProvidersDiscoverView)
    view.flash.assert_message('At least 1 item must be selected for discovery')


@pytest.mark.sauce
def test_discovery_cancelled_validation_infra(appliance):
    """ Tests that the flash message is correct when discovery is cancelled."""
    collection = appliance.collections.infra_providers
    collection.discover(None, cancel=True)
    view = appliance.browser.create_view(InfraProvidersView)
    view.flash.assert_success_message('Infrastructure Providers '
                                      'Discovery was cancelled by the user')


@pytest.mark.sauce
def test_add_cancelled_validation_infra(appliance):
    """Tests that the flash message is correct when add is cancelled."""
    appliance.collections.infra_providers.create(prov_class=VMwareProvider, cancel=True)
    view = appliance.browser.create_view(InfraProvidersView)
    view.flash.assert_success_message('Add of Infrastructure Provider was cancelled by the user')


@pytest.mark.sauce
def test_type_required_validation_infra(appliance):
    """Test to validate type while adding a provider"""
    with pytest.raises(AssertionError):
        appliance.collections.infra_providers.create(prov_class=VMwareProvider)
    view = appliance.browser.create_view(InfraProviderAddView)
    assert not view.add.active


def test_name_required_validation_infra(appliance):
    """Tests to validate the name while adding a provider"""
    collections = appliance.collections.infra_providers
    endpoint = VirtualCenterEndpoint(hostname=fauxfactory.gen_alphanumeric(5))

    with pytest.raises(AssertionError):
        collections.create(prov_class=VMwareProvider, name=None, endpoints=endpoint)

    view = appliance.browser.create_view(InfraProviderAddView)
    assert view.name.help_block == "Required"
    assert not view.add.active


def test_host_name_required_validation_infra(appliance):
    """Test to validate the hostname while adding a provider"""
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
    """Test to validate max character for name field"""
    request.addfinalizer(lambda: infra_provider.delete_if_exists(cancel=False))
    name = fauxfactory.gen_alphanumeric(255)
    with update(infra_provider):
        infra_provider.name = name
    assert infra_provider.exists


def test_host_name_max_character_validation_infra(appliance):
    """Test to validate max character for host name field"""
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
    """Test to validate max character for api port field"""
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


@pytest.mark.rhv1
@pytest.mark.usefixtures('has_no_infra_providers')
@pytest.mark.meta(blockers=[BZ(1559796, forced_streams=['5.8', '5.9'],
    unblock=lambda provider: not provider.one_of(RHEVMProvider))])
@pytest.mark.tier(1)
def test_providers_discovery(request, appliance, provider):
    """Tests provider discovery

    Metadata:
        test_flag: crud
    """
    appliance.collections.infra_providers.discover(provider, cancel=False,
                                                   start_ip=provider.start_ip,
                                                   end_ip=provider.end_ip)
    view = provider.browser.create_view(InfraProvidersView)
    view.flash.assert_success_message('Infrastructure Providers: Discovery successfully initiated')

    request.addfinalizer(InfraProvider.clear_providers)
    appliance.collections.infra_providers.wait_for_a_provider()


@pytest.mark.rhv1
@pytest.mark.usefixtures('has_no_infra_providers')
def test_infra_provider_add_with_bad_credentials(provider):
    """Tests provider add with bad credentials

    Metadata:
        test_flag: crud
    """
    provider.default_endpoint.credentials = Credential(
        principal='bad',
        secret='reallybad',
        verify_secret='reallybad'
    )

    with pytest.raises(AssertionError, match=provider.bad_credentials_error_msg):
        provider.create(validate_credentials=True)


@pytest.mark.rhv1
@pytest.mark.usefixtures('has_no_infra_providers')
@pytest.mark.tier(1)
@pytest.mark.smoke
@pytest.mark.meta(blockers=[BZ(1450527, unblock=lambda provider: provider.type != 'scvmm')])
def test_infra_provider_crud(provider):
    """Tests provider add with good credentials

    Metadata:
        test_flag: crud
    """
    provider.create()
    # Fails on upstream, all provider types - BZ1087476
    provider.validate_stats(ui=True)

    old_name = provider.name
    with update(provider):
        provider.name = str(uuid.uuid4())  # random uuid

    with update(provider):
        provider.name = old_name  # old name

    provider.delete(cancel=False)
    provider.wait_for_delete()


@pytest.mark.rhv1
@pytest.mark.usefixtures('has_no_infra_providers')
@pytest.mark.tier(1)
@pytest.mark.parametrize('verify_tls', [False, True], ids=['no_tls', 'tls'])
@pytest.mark.uncollectif(lambda provider:
    not (provider.one_of(RHEVMProvider) and
         provider.endpoints.get('default').__dict__.get('verify_tls')))
def test_provider_rhv_create_delete_tls(request, provider, verify_tls):
    """Tests RHV provider creation with and without TLS encryption

    Metadata:
       test_flag: crud
    """
    prov = copy(provider)
    request.addfinalizer(lambda: prov.delete_if_exists(cancel=False))

    if not verify_tls:
        endpoints = deepcopy(prov.endpoints)
        endpoints['default'].verify_tls = False
        endpoints['default'].ca_certs = None

        prov.endpoints = endpoints
        prov.name = "{}-no-tls".format(provider.name)

    prov.create()
    prov.validate_stats(ui=True)

    prov.delete(cancel=False)
    prov.wait_for_delete()


def test_infrastructure_add_provider_trailing_whitespaces(appliance):
    """Test to validate the hostname and username should be without whitespaces"""
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

    if appliance.version >= '5.9.2':
        assert view.osp_infra.is_displayed
        view.osp_infra.click()
        assert view.osp_infra.selected
        view.osp_infra.click()
        assert not view.osp_infra.selected

    view.start.click()
    assert view.flash.assert_message("At least 1 item must be selected for discovery")

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
