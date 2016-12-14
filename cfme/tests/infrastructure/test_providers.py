# -*- coding: utf-8 -*-
import fauxfactory
import uuid

import pytest

from manageiq_client.api import APIException

import cfme.web_ui.flash as flash
import utils.error as error
import cfme.fixtures.pytest_selenium as sel
from cfme.common.provider import BaseProvider
from cfme.exceptions import FlashMessageException
from cfme.infrastructure.provider import discover, wait_for_a_provider, InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from utils import testgen, providers, version
from utils.update import update
from cfme import test_requirements

pytest_generate_tests = testgen.generate([InfraProvider], scope="function")


@pytest.fixture(scope="module")
def setup_a_provider():
    return providers.setup_a_provider_by_class(prov_class=InfraProvider, validate=True,
                                               check_existing=True)


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
def test_name_max_character_validation(request, setup_a_provider):
    """Test to validate max character for name field"""
    provider = setup_a_provider
    request.addfinalizer(lambda: provider.delete_if_exists(cancel=False))
    name = fauxfactory.gen_alphanumeric(255)
    provider.update({'name': name})
    provider.name = name
    assert provider.exists


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
    request.addfinalizer(lambda: BaseProvider.clear_providers_by_class(InfraProvider))
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
    def custom_attributes(self, rest_api, setup_a_provider):
        provider = rest_api.collections.providers[0]
        attrs = provider.custom_attributes.action.add(
            {"name": "ca_name1", "value": "ca_value1"}, {"name": "ca_name2", "value": "ca_value2"})

        yield attrs

        try:
            provider.custom_attributes.action.delete(*attrs)
        except APIException:
            pass

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    def test_add_custom_attributes(self, custom_attributes):
        """Test adding custom attributes to provider using REST API."""
        assert len(custom_attributes) == 2
        assert custom_attributes[0].name == "ca_name1" and custom_attributes[0].value == "ca_value1"
        assert custom_attributes[1].name == "ca_name2" and custom_attributes[1].value == "ca_value2"

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_delete_custom_attributes(self, rest_api, custom_attributes, from_detail):
        """Test deleting custom attributes using REST API."""
        if from_detail:
            for ent in custom_attributes:
                ent.action.delete()
                with error.expected("ActiveRecord::RecordNotFound"):
                    ent.action.delete()
        else:
            provider = rest_api.collections.providers[0]
            provider.custom_attributes.action.delete(*custom_attributes)
            with error.expected("ActiveRecord::RecordNotFound"):
                provider.custom_attributes.action.delete(*custom_attributes)

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.tier(3)
    @test_requirements.rest
    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_edit_custom_attributes(self, rest_api, custom_attributes, from_detail):
        """Test editing custom attributes using REST API."""
        attrs0 = {"name": "ca_new_name1", "value": "ca_new_value1"}
        attrs1 = {"name": "ca_new_name2", "value": "ca_new_value2"}
        if from_detail:
            changed_attrs = []
            changed_attrs.append(custom_attributes[0].action.edit(**attrs0))
            changed_attrs.append(custom_attributes[1].action.edit(**attrs1))
        else:
            attrs0.update(custom_attributes[0]._ref_repr())
            attrs1.update(custom_attributes[1]._ref_repr())
            provider = rest_api.collections.providers[0]
            changed_attrs = provider.custom_attributes.action.edit(attrs0, attrs1)
        assert changed_attrs[0].name == "ca_new_name1" and changed_attrs[0].value == "ca_new_value1"
        assert changed_attrs[1].name == "ca_new_name2" and changed_attrs[1].value == "ca_new_value2"
