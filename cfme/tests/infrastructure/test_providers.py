# -*- coding: utf-8 -*-
import uuid
import fauxfactory

import pytest

from copy import copy, deepcopy

from cfme.utils import error
from cfme.base.credential import Credential
from cfme.common.provider_views import (InfraProviderAddView,
                                        InfraProvidersView,
                                        InfraProvidersDiscoverView)
from cfme.infrastructure.provider import discover, wait_for_a_provider, InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider, RHEVMEndpoint
from cfme.infrastructure.provider.virtualcenter import VMwareProvider, VirtualCenterEndpoint
from cfme.utils import testgen, version
from cfme.utils.update import update
from cfme.utils.blockers import BZ
from cfme import test_requirements

pytest_generate_tests = testgen.generate([InfraProvider], scope="function")


@pytest.mark.tier(3)
@pytest.mark.sauce
@test_requirements.discovery
def test_empty_discovery_form_validation(appliance):
    """ Tests that the flash message is correct when discovery form is empty."""
    discover(None)
    view = appliance.browser.create_view(InfraProvidersDiscoverView)
    view.flash.assert_message('At least 1 item must be selected for discovery')


@pytest.mark.tier(3)
@pytest.mark.sauce
@test_requirements.provider_discovery
def test_discovery_cancelled_validation(appliance):
    """ Tests that the flash message is correct when discovery is cancelled."""
    discover(None, cancel=True)
    view = appliance.browser.create_view(InfraProvidersView)
    view.flash.assert_success_message('Infrastructure Providers '
                                      'Discovery was cancelled by the user')


@pytest.mark.tier(3)
@pytest.mark.sauce
@test_requirements.provider_discovery
def test_add_cancelled_validation(appliance):
    """Tests that the flash message is correct when add is cancelled."""
    prov = VMwareProvider()
    prov.create(cancel=True)
    view = appliance.browser.create_view(InfraProvidersView)
    view.flash.assert_success_message('Add of Infrastructure Provider was cancelled by the user')


@pytest.mark.tier(3)
@pytest.mark.sauce
@test_requirements.provider_discovery
def test_type_required_validation():
    """Test to validate type while adding a provider"""
    prov = InfraProvider()
    with pytest.raises(AssertionError):
        prov.create()

    view = prov.create_view(InfraProviderAddView)
    assert not view.add.active


@pytest.mark.tier(3)
@test_requirements.provider_discovery
def test_name_required_validation():
    """Tests to validate the name while adding a provider"""
    endpoint = VirtualCenterEndpoint(hostname=fauxfactory.gen_alphanumeric(5))
    prov = VMwareProvider(
        name=None,
        endpoints=endpoint)

    with pytest.raises(AssertionError):
        prov.create()

    view = prov.create_view(InfraProviderAddView)
    assert view.name.help_block == "Required"
    assert not view.add.active


@pytest.mark.tier(3)
@test_requirements.provider_discovery
def test_host_name_required_validation():
    """Test to validate the hostname while adding a provider"""
    endpoint = VirtualCenterEndpoint(hostname=None)
    prov = VMwareProvider(
        name=fauxfactory.gen_alphanumeric(5),
        endpoints=endpoint)

    with pytest.raises(AssertionError):
        prov.create()

    view = prov.create_view(prov.endpoints_form)
    assert view.hostname.help_block == "Required"
    view = prov.create_view(InfraProviderAddView)
    assert not view.add.active


@pytest.mark.tier(3)
@test_requirements.provider_discovery
def test_name_max_character_validation(request, infra_provider):
    """Test to validate max character for name field"""
    request.addfinalizer(lambda: infra_provider.delete_if_exists(cancel=False))
    name = fauxfactory.gen_alphanumeric(255)
    with update(infra_provider):
        infra_provider.name = name
    assert infra_provider.exists


@pytest.mark.tier(3)
@test_requirements.provider_discovery
def test_host_name_max_character_validation():
    """Test to validate max character for host name field"""
    endpoint = VirtualCenterEndpoint(hostname=fauxfactory.gen_alphanumeric(256))
    prov = VMwareProvider(name=fauxfactory.gen_alphanumeric(5), endpoints=endpoint)
    try:
        prov.create()
    except AssertionError:
        view = prov.create_view(prov.endpoints_form)
        assert view.hostname.value == prov.hostname[0:255]


@pytest.mark.tier(3)
@test_requirements.provider_discovery
def test_api_port_max_character_validation():
    """Test to validate max character for api port field"""
    endpoint = RHEVMEndpoint(hostname=fauxfactory.gen_alphanumeric(5),
                             api_port=fauxfactory.gen_alphanumeric(16),
                             verify_tls=None,
                             ca_certs=None)
    prov = RHEVMProvider(name=fauxfactory.gen_alphanumeric(5), endpoints=endpoint)
    try:
        prov.create()
    except AssertionError:
        view = prov.create_view(prov.endpoints_form)
        text = view.default.api_port.value
        assert text == prov.default_endpoint.api_port[0:15]


@pytest.mark.usefixtures('has_no_infra_providers')
@pytest.mark.tier(1)
@test_requirements.provider_discovery
def test_providers_discovery(request, provider):
    """Tests provider discovery

    Metadata:
        test_flag: crud
    """
    provider.discover()
    view = provider.create_view(InfraProvidersView)
    view.flash.assert_success_message('Infrastructure Providers: Discovery successfully initiated')

    request.addfinalizer(InfraProvider.clear_providers)
    wait_for_a_provider()


@pytest.mark.uncollectif(lambda provider: provider.type == 'rhevm', 'blocker=1399622')
@pytest.mark.tier(3)
@pytest.mark.usefixtures('has_no_infra_providers')
@test_requirements.provider_discovery
def test_provider_add_with_bad_credentials(provider):
    """Tests provider add with bad credentials

    Metadata:
        test_flag: crud
    """
    provider.default_endpoint.credentials = Credential(
        principal='bad',
        secret='reallybad',
        verify_secret='reallybad'
    )

    with error.expected(provider.bad_credentials_error_msg):
        provider.create(validate_credentials=True)


@pytest.mark.usefixtures('has_no_infra_providers')
@pytest.mark.tier(1)
@test_requirements.provider_discovery
@pytest.mark.meta(blockers=[BZ(1450527, unblock=lambda provider: provider.type != 'scvmm')])
def test_provider_crud(provider):
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


@pytest.mark.usefixtures('has_no_infra_providers')
@pytest.mark.tier(1)
@test_requirements.provider_discovery
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


class TestProvidersRESTAPI(object):
    @pytest.yield_fixture(scope="function")
    def custom_attributes(self, appliance, infra_provider):
        provider = appliance.rest_api.collections.providers.get(name=infra_provider.name)
        body = []
        attrs_num = 2
        for _ in range(attrs_num):
            uid = fauxfactory.gen_alphanumeric(5)
            body.append({
                'name': 'ca_name_{}'.format(uid),
                'value': 'ca_value_{}'.format(uid)
            })
        attrs = provider.custom_attributes.action.add(*body)
        assert len(attrs) == attrs_num

        yield attrs, provider

        provider.custom_attributes.reload()
        ids = [attr.id for attr in attrs]
        delete_attrs = [attr for attr in provider.custom_attributes if attr.id in ids]
        if delete_attrs:
            provider.custom_attributes.action.delete(*delete_attrs)

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    def test_add_custom_attributes(self, appliance, custom_attributes):
        """Test adding custom attributes to provider using REST API.

        Metadata:
            test_flag: rest
        """
        attributes, provider = custom_attributes
        for attr in attributes:
            record = provider.custom_attributes.get(id=attr.id)
            assert appliance.rest_api.response.status_code == 200
            assert record.name == attr.name
            assert record.value == attr.value

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    def test_delete_custom_attributes_from_detail_post(self, appliance, custom_attributes):
        """Test deleting custom attributes from detail using POST method.

        Metadata:
            test_flag: rest
        """
        attributes, _ = custom_attributes
        for entity in attributes:
            entity.action.delete.POST()
            assert appliance.rest_api.response
            with error.expected('ActiveRecord::RecordNotFound'):
                entity.action.delete.POST()
            assert appliance.rest_api.response.status_code == 404

    # BZ 1422596 was not fixed for versions < 5.9
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.9')
    @pytest.mark.tier(3)
    @test_requirements.rest
    def test_delete_custom_attributes_from_detail_delete(self, appliance, custom_attributes):
        """Test deleting custom attributes from detail using DELETE method.

        Metadata:
            test_flag: rest
        """
        attributes, _ = custom_attributes
        for entity in attributes:
            entity.action.delete.DELETE()
            assert appliance.rest_api.response
            with error.expected('ActiveRecord::RecordNotFound'):
                entity.action.delete.DELETE()
            assert appliance.rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    def test_delete_custom_attributes_from_collection(self, appliance, custom_attributes):
        """Test deleting custom attributes from collection using REST API.

        Metadata:
            test_flag: rest
        """
        attributes, provider = custom_attributes
        provider.custom_attributes.action.delete(*attributes)
        assert appliance.rest_api.response.status_code == 200
        with error.expected('ActiveRecord::RecordNotFound'):
            provider.custom_attributes.action.delete(*attributes)
        assert appliance.rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    def test_delete_single_custom_attribute_from_collection(self, appliance, custom_attributes):
        """Test deleting single custom attribute from collection using REST API.

        Metadata:
            test_flag: rest
        """
        attributes, provider = custom_attributes
        attribute = attributes[0]
        provider.custom_attributes.action.delete(attribute)
        assert appliance.rest_api.response.status_code == 200
        with error.expected('ActiveRecord::RecordNotFound'):
            provider.custom_attributes.action.delete(attribute)
        assert appliance.rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_edit_custom_attributes(self, appliance, custom_attributes, from_detail):
        """Test editing custom attributes using REST API.

        Metadata:
            test_flag: rest
        """
        attributes, provider = custom_attributes
        response_len = len(attributes)
        body = []
        for _ in range(response_len):
            uid = fauxfactory.gen_alphanumeric(5)
            body.append({
                'name': 'ca_name_{}'.format(uid),
                'value': 'ca_value_{}'.format(uid),
                'section': 'metadata'
            })
        if from_detail:
            edited = []
            for i in range(response_len):
                edited.append(attributes[i].action.edit(**body[i]))
                assert appliance.rest_api.response.status_code == 200
        else:
            for i in range(response_len):
                body[i].update(attributes[i]._ref_repr())
            edited = provider.custom_attributes.action.edit(*body)
            assert appliance.rest_api.response.status_code == 200
        assert len(edited) == response_len
        for i in range(response_len):
            assert edited[i].name == body[i]['name']
            assert edited[i].value == body[i]['value']

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_edit_custom_attributes_bad_section(self, appliance, custom_attributes, from_detail):
        """Test that editing custom attributes using REST API and adding invalid section fails.

        Metadata:
            test_flag: rest
        """
        attributes, provider = custom_attributes
        response_len = len(attributes)
        body = []
        for _ in range(response_len):
            body.append({'section': 'bad_section'})
        if from_detail:
            for i in range(response_len):
                with error.expected('Api::BadRequestError'):
                    attributes[i].action.edit(**body[i])
                assert appliance.rest_api.response.status_code == 400
        else:
            for i in range(response_len):
                body[i].update(attributes[i]._ref_repr())
            with error.expected('Api::BadRequestError'):
                provider.custom_attributes.action.edit(*body)
            assert appliance.rest_api.response.status_code == 400

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    def test_add_custom_attributes_bad_section(self, appliance, infra_provider):
        """Test that adding custom attributes with invalid section
        to provider using REST API fails.

        Metadata:
            test_flag: rest
        """
        provider = appliance.rest_api.collections.providers.get(name=infra_provider.name)
        uid = fauxfactory.gen_alphanumeric(5)
        body = {
            'name': 'ca_name_{}'.format(uid),
            'value': 'ca_value_{}'.format(uid),
            'section': 'bad_section'
        }
        with error.expected('Api::BadRequestError'):
            provider.custom_attributes.action.add(body)
        assert appliance.rest_api.response.status_code == 400
