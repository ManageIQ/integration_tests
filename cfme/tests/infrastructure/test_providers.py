# -*- coding: utf-8 -*-
import fauxfactory
import uuid

import pytest

from manageiq_client.api import APIException

import cfme.web_ui.flash as flash
import utils.error as error
import cfme.fixtures.pytest_selenium as sel
from cfme.exceptions import FlashMessageException
from cfme.infrastructure.provider import discover, wait_for_a_provider, InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from utils import testgen, version
from utils.update import update
from utils.log import logger
from cfme import test_requirements

pytest_generate_tests = testgen.generate([InfraProvider], scope="function")


@pytest.mark.tier(3)
@pytest.mark.sauce
@test_requirements.discovery
def test_empty_discovery_form_validation():
    """ Tests that the flash message is correct when discovery form is empty."""
    discover(None)
    flash.assert_message_match('At least 1 item must be selected for discovery')


@pytest.mark.tier(3)
@pytest.mark.sauce
@test_requirements.provider_discovery
def test_discovery_cancelled_validation():
    """ Tests that the flash message is correct when discovery is cancelled."""
    discover(None, cancel=True)
    flash.assert_message_match('Infrastructure Providers Discovery was cancelled by the user')


@pytest.mark.tier(3)
@pytest.mark.sauce
@test_requirements.provider_discovery
def test_add_cancelled_validation():
    """Tests that the flash message is correct when add is cancelled."""
    prov = VMwareProvider()
    prov.create(cancel=True)
    if version.current_version() >= 5.6:
        msg = 'Add of Infrastructure Provider was cancelled by the user'
    else:
        msg = 'Add of new Infrastructure Provider was cancelled by the user'
    flash.assert_message_match(msg)


@pytest.mark.tier(3)
@pytest.mark.sauce
@test_requirements.provider_discovery
def test_type_required_validation():
    """Test to validate type while adding a provider"""
    prov = InfraProvider()
    err = version.pick(
        {version.LOWEST: 'Type is required',
         '5.6': FlashMessageException})

    with error.expected(err):
        prov.create()

    if version.current_version() >= 5.6:
        assert prov.add_provider_button.is_dimmed


@pytest.mark.tier(3)
@test_requirements.provider_discovery
def test_name_required_validation():
    """Tests to validate the name while adding a provider"""
    prov = VMwareProvider(
        name=None,
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address='10.10.10.10')

    err = version.pick(
        {version.LOWEST: "Name can't be blank",
         '5.6': FlashMessageException})

    with error.expected(err):
        prov.create()

    if version.current_version() >= 5.6:
        assert prov.properties_form.name_text.angular_help_block == "Required"
        assert prov.add_provider_button.is_dimmed


@pytest.mark.tier(3)
@test_requirements.provider_discovery
def test_host_name_required_validation():
    """Test to validate the hostname while adding a provider"""
    prov = VMwareProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=None,
        ip_address='10.10.10.11')

    err = version.pick(
        {version.LOWEST: "Host Name can't be blank",
         '5.6': FlashMessageException})

    with error.expected(err):
        prov.create()

    if version.current_version() >= 5.6:
        assert prov.properties_form.hostname_text.angular_help_block == "Required"
        assert prov.add_provider_button.is_dimmed


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1209756])
@pytest.mark.uncollectif(lambda: version.current_version() > "5.4.0.0.24")
def test_ip_required_validation():
    """Test to validate the ip address while adding a provider"""
    prov = VMwareProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address=None)

    with error.expected("IP Address can't be blank"):
        prov.create()


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
    prov = VMwareProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(256),
        ip_address='10.10.10.13')
    try:
        prov.create()
    except FlashMessageException:
        element = sel.move_to_element(prov.properties_form.locators["hostname_text"])
        text = element.get_attribute('value')
        assert text == prov.hostname[0:255]


@pytest.mark.tier(3)
@test_requirements.provider_discovery
def test_api_port_max_character_validation():
    """Test to validate max character for api port field"""
    prov = RHEVMProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address='10.10.10.15',
        api_port=fauxfactory.gen_alphanumeric(16))
    try:
        prov.create()
    except FlashMessageException:
        element = sel.move_to_element(prov.properties_form.locators["api_port"])
        text = element.get_attribute('value')
        assert text == prov.api_port[0:15]


@pytest.mark.usefixtures('has_no_infra_providers')
@pytest.mark.tier(1)
@test_requirements.provider_discovery
def test_providers_discovery(request, provider):
    """Tests provider discovery

    Metadata:
        test_flag: crud
    """
    provider.discover()
    flash.assert_message_match('Infrastructure Providers: Discovery successfully initiated')
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
    provider.credentials['default'] = provider.Credential(
        principal='bad',
        secret='reallybad',
        verify_secret='reallybad'
    )
    if isinstance(provider, VMwareProvider):
        with error.expected('Cannot complete login due to an incorrect user name or password.'):
            provider.create(validate_credentials=True)
    elif isinstance(provider, RHEVMProvider):
        error_message = version.pick({
            '5.4': '401 Unauthorized',
            '5.5': ('Credential validation was not successful: '
                'Login failed due to a bad username or password.'),
            '5.6': ('Credential validation was not successful: '
                'Incorrect user name or password.'),
        })
        with error.expected(error_message):
            provider.create(validate_credentials=True)


@pytest.mark.usefixtures('has_no_infra_providers')
@pytest.mark.tier(1)
@test_requirements.provider_discovery
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


class TestProvidersRESTAPI(object):
    @pytest.yield_fixture(scope="function")
    def custom_attributes(self, rest_api, infra_provider):
        provider = rest_api.collections.providers.get(name=infra_provider.name)
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

        log_warn = False
        for attr in attrs:
            try:
                provider.custom_attributes.action.delete(attr)
            except APIException:
                # custom attributes can be deleted by tests, just log warning
                log_warn = True
        if log_warn:
            logger.warning("Failed to delete custom attribute.")

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    def test_add_custom_attributes(self, rest_api, custom_attributes):
        """Test adding custom attributes to provider using REST API.

        Metadata:
            test_flag: rest
        """
        attributes, provider = custom_attributes
        for attr in attributes:
            record = provider.custom_attributes.get(id=attr.id)
            assert rest_api.response.status_code == 200
            assert record.name == attr.name
            assert record.value == attr.value

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    @pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
    def test_delete_custom_attributes_from_detail(self, rest_api, custom_attributes, method):
        """Test deleting custom attributes from detail using REST API.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == 'delete' else 200
        attributes, _ = custom_attributes
        for entity in attributes:
            entity.action.delete(force_method=method)
            assert rest_api.response.status_code == status
            with error.expected('ActiveRecord::RecordNotFound'):
                entity.action.delete(force_method=method)
            assert rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    def test_delete_custom_attributes_from_collection(self, rest_api, custom_attributes):
        """Test deleting custom attributes from collection using REST API.

        Metadata:
            test_flag: rest
        """
        attributes, provider = custom_attributes
        provider.custom_attributes.action.delete(*attributes)
        assert rest_api.response.status_code == 200
        with error.expected('ActiveRecord::RecordNotFound'):
            provider.custom_attributes.action.delete(*attributes)
        assert rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    def test_delete_single_custom_attribute_from_collection(self, rest_api, custom_attributes):
        """Test deleting single custom attribute from collection using REST API.

        Metadata:
            test_flag: rest
        """
        attributes, provider = custom_attributes
        attribute = attributes[0]
        provider.custom_attributes.action.delete(attribute)
        assert rest_api.response.status_code == 200
        with error.expected('ActiveRecord::RecordNotFound'):
            provider.custom_attributes.action.delete(attribute)
        assert rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_edit_custom_attributes(self, rest_api, custom_attributes, from_detail):
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
                assert rest_api.response.status_code == 200
        else:
            for i in range(response_len):
                body[i].update(attributes[i]._ref_repr())
            edited = provider.custom_attributes.action.edit(*body)
            assert rest_api.response.status_code == 200
        assert len(edited) == response_len
        for i in range(response_len):
            assert edited[i].name == body[i]['name']
            assert edited[i].value == body[i]['value']

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_edit_custom_attributes_bad_section(self, rest_api, custom_attributes, from_detail):
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
                assert rest_api.response.status_code == 400
        else:
            for i in range(response_len):
                body[i].update(attributes[i]._ref_repr())
            with error.expected('Api::BadRequestError'):
                provider.custom_attributes.action.edit(*body)
            assert rest_api.response.status_code == 400

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    def test_add_custom_attributes_bad_section(self, rest_api, infra_provider):
        """Test that adding custom attributes with invalid section
        to provider using REST API fails.

        Metadata:
            test_flag: rest
        """
        provider = rest_api.collections.providers.get(name=infra_provider.name)
        uid = fauxfactory.gen_alphanumeric(5)
        body = {
            'name': 'ca_name_{}'.format(uid),
            'value': 'ca_value_{}'.format(uid),
            'section': 'bad_section'
        }
        with error.expected('Api::BadRequestError'):
            provider.custom_attributes.action.add(body)
        assert rest_api.response.status_code == 400
