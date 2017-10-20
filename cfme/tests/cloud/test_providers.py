# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621
import uuid
import fauxfactory

import pytest

from cfme.utils import error
from cfme.base.credential import Credential
from cfme.cloud.provider import discover, wait_for_a_provider, CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider, RHOSEndpoint
from cfme.common.provider_views import (CloudProviderAddView,
                                        CloudProvidersView,
                                        CloudProvidersDiscoverView)
from cfme import test_requirements

from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update
from cfme.rest.gen_data import arbitration_profiles as _arbitration_profiles
from cfme.rest.gen_data import _creating_skeleton as creating_skeleton

pytestmark = [pytest.mark.provider([CloudProvider], scope="function")]


@pytest.mark.tier(3)
@test_requirements.discovery
def test_empty_discovery_form_validation(appliance):
    """ Tests that the flash message is correct when discovery form is empty."""
    discover(None, EC2Provider)
    view = appliance.browser.create_view(CloudProvidersDiscoverView)
    view.flash.assert_message('Username is required')


@pytest.mark.tier(3)
@test_requirements.discovery
def test_discovery_cancelled_validation(appliance):
    """ Tests that the flash message is correct when discovery is cancelled."""
    discover(None, EC2Provider, cancel=True)
    view = appliance.browser.create_view(CloudProvidersView)
    view.flash.assert_success_message('Cloud Providers Discovery was cancelled by the user')


@pytest.mark.tier(3)
@test_requirements.discovery
def test_add_cancelled_validation(request):
    """Tests that the flash message is correct when add is cancelled."""
    prov = EC2Provider()
    request.addfinalizer(prov.delete_if_exists)
    prov.create(cancel=True)
    view = prov.browser.create_view(CloudProvidersView)
    view.flash.assert_success_message('Add of Cloud Provider was cancelled by the user')


@pytest.mark.tier(3)
def test_password_mismatch_validation(appliance):
    cred = Credential(
        principal=fauxfactory.gen_alphanumeric(5),
        secret=fauxfactory.gen_alphanumeric(5),
        verify_secret=fauxfactory.gen_alphanumeric(7))

    discover(cred, EC2Provider)
    view = appliance.browser.create_view(CloudProvidersView)
    view.flash.assert_message('Password/Verify Password do not match')


@pytest.mark.tier(3)
@pytest.mark.uncollect()
@pytest.mark.usefixtures('has_no_cloud_providers')
@test_requirements.discovery
def test_providers_discovery_amazon(appliance):
    # This test was being uncollected anyway, and needs to be parametrized and not directory call
    # out to specific credential keys
    # amazon_creds = get_credentials_from_config('cloudqe_amazon')
    # discover(amazon_creds, EC2Provider)

    view = appliance.browser.create_view(CloudProvidersView)
    view.flash.assert_success_message('Amazon Cloud Providers: Discovery successfully initiated')
    wait_for_a_provider()


@pytest.mark.tier(3)
@pytest.mark.usefixtures('has_no_cloud_providers')
@test_requirements.discovery
def test_provider_add_with_bad_credentials(provider):
    """ Tests provider add with bad credentials

    Metadata:
        test_flag: crud
    """
    default_credentials = provider.default_endpoint.credentials

    # default settings
    flash = 'Login failed due to a bad username or password.'
    default_credentials.principal = "bad"
    default_credentials.secret = 'notyourday'

    if provider.one_of(AzureProvider):
        flash = (
            "Credential validation was not successful: Incorrect credentials - "
            "check your Azure Client ID and Client Key"
        )
        default_credentials.principal = str(uuid.uuid4())
        default_credentials.secret = 'notyourday'
    elif provider.one_of(GCEProvider):
        flash = 'Credential validation was not successful: Invalid Google JSON key'
        default_credentials.service_account = '{"test": "bad"}'
    elif provider.one_of(OpenStackProvider):
        for endp_name in provider.endpoints.keys():
            if endp_name != 'default':
                del provider.endpoints[endp_name]

    with error.expected(flash):
        provider.create(validate_credentials=True)


@pytest.mark.tier(2)
@pytest.mark.usefixtures('has_no_cloud_providers')
@test_requirements.discovery
def test_provider_crud(provider):
    """ Tests provider add with good credentials

    Metadata:
        test_flag: crud
    """
    provider.create()
    provider.validate_stats(ui=True)

    old_name = provider.name
    with update(provider):
        provider.name = str(uuid.uuid4())  # random uuid

    with update(provider):
        provider.name = old_name  # old name

    provider.delete(cancel=False)
    provider.wait_for_delete()


@pytest.mark.tier(3)
@test_requirements.discovery
def test_type_required_validation(request):
    """Test to validate type while adding a provider"""
    prov = CloudProvider()
    request.addfinalizer(prov.delete_if_exists)
    view = navigate_to(prov, 'Add')
    view.fill({'name': 'foo'})
    assert not view.add.active


@pytest.mark.tier(3)
@test_requirements.discovery
def test_name_required_validation(request):
    """Tests to validate the name while adding a provider"""
    prov = EC2Provider(
        name=None,
        region='US East (Northern Virginia)')

    request.addfinalizer(prov.delete_if_exists)
    with pytest.raises(AssertionError):
        prov.create()
    view = prov.create_view(CloudProviderAddView)
    assert view.name.help_block == "Required"
    assert not view.add.active


@pytest.mark.tier(3)
def test_region_required_validation(request, soft_assert):
    """Tests to validate the region while adding a provider"""
    prov = EC2Provider(name=fauxfactory.gen_alphanumeric(5), region=None)

    request.addfinalizer(prov.delete_if_exists)
    with pytest.raises(AssertionError):
        prov.create()
        view = prov.create_view(CloudProviderAddView)
        soft_assert(view.region.help_block == "Required")


@pytest.mark.tier(3)
@test_requirements.discovery
def test_host_name_required_validation(request):
    """Test to validate the hostname while adding a provider"""
    prov = OpenStackProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=None,
        ip_address=fauxfactory.gen_ipaddr(prefix=[10]))

    request.addfinalizer(prov.delete_if_exists)
    # It must raise an exception because it keeps on the form
    with pytest.raises(AssertionError):
        prov.create()
    endpoints = prov.create_view(prov.endpoints_form)
    assert endpoints.default.hostname.help_block == "Required"


@pytest.mark.tier(3)
def test_api_port_blank_validation(request):
    """Test to validate blank api port while adding a provider"""
    endpoint = RHOSEndpoint(hostname=fauxfactory.gen_alphanumeric(5),
                            ip_address=fauxfactory.gen_ipaddr(prefix=[10]),
                            api_port='',
                            security_protocol='Non-SSL')
    prov = OpenStackProvider(name=fauxfactory.gen_alphanumeric(5), endpoints=endpoint)

    request.addfinalizer(prov.delete_if_exists)
    # It must raise an exception because it keeps on the form
    with pytest.raises(AssertionError):
        prov.create()
    endpoints = prov.create_view(prov.endpoints_form)
    assert endpoints.default.api_port.help_block == "Required"


@pytest.mark.tier(3)
def test_user_id_max_character_validation():
    cred = Credential(principal=fauxfactory.gen_alphanumeric(51), secret='')
    discover(cred, EC2Provider)


@pytest.mark.tier(3)
def test_password_max_character_validation():
    password = fauxfactory.gen_alphanumeric(51)
    cred = Credential(
        principal=fauxfactory.gen_alphanumeric(5),
        secret=password,
        verify_secret=password)
    discover(cred, EC2Provider)


@pytest.mark.tier(3)
@test_requirements.discovery
def test_name_max_character_validation(request, cloud_provider):
    """Test to validate that provider can have up to 255 characters in name"""
    request.addfinalizer(lambda: cloud_provider.delete_if_exists(cancel=False))
    name = fauxfactory.gen_alphanumeric(255)
    with update(cloud_provider):
        cloud_provider.name = name
    assert cloud_provider.exists


@pytest.mark.tier(3)
def test_hostname_max_character_validation():
    """Test to validate max character for hostname field"""
    endpoint = RHOSEndpoint(hostname=fauxfactory.gen_alphanumeric(256),
                            api_port=None,
                            security_protocol=None)
    prov = OpenStackProvider(name=fauxfactory.gen_alphanumeric(5), endpoints=endpoint)
    try:
        prov.create()
    except AssertionError:
        endpoints = prov.create_view(prov.endpoints_form)
        assert endpoints.default.hostname.value == prov.hostname[0:255]


@pytest.mark.tier(3)
@test_requirements.discovery
def test_api_port_max_character_validation():
    """Test to validate max character for api port field"""
    endpoint = RHOSEndpoint(hostname=fauxfactory.gen_alphanumeric(5),
                            api_port=fauxfactory.gen_alphanumeric(16),
                            security_protocol='Non-SSL')
    prov = OpenStackProvider(name=fauxfactory.gen_alphanumeric(5), endpoints=endpoint)
    try:
        prov.create()
    except AssertionError:
        view = prov.create_view(prov.endpoints_form)
        text = view.default.api_port.value
        assert text == prov.default_endpoint.api_port[0:15]


@pytest.mark.tier(3)
def test_openstack_provider_has_api_version():
    """Check whether the Keystone API version field is present for Openstack."""
    prov = CloudProvider()
    view = navigate_to(prov, 'Add')
    view.fill({"prov_type": "OpenStack"})
    assert view.api_version.is_displayed, "API version select is not visible"


class TestProvidersRESTAPI(object):
    @pytest.fixture(scope="function")
    def arbitration_profiles(self, request, appliance, cloud_provider):
        num_profiles = 2
        response = _arbitration_profiles(
            request, appliance.rest_api, cloud_provider, num=num_profiles)
        assert appliance.rest_api.response.status_code == 200
        assert len(response) == num_profiles

        return response

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_cloud_networks_query(self, cloud_provider, appliance, from_detail):
        """Tests querying cloud providers and cloud_networks collection for network info.

        Metadata:
            test_flag: rest
        """
        if from_detail:
            networks = appliance.rest_api.collections.providers.get(
                name=cloud_provider.name).cloud_networks
        else:
            networks = appliance.rest_api.collections.cloud_networks
        assert appliance.rest_api.response.status_code == 200
        assert networks
        assert len(networks) == networks.subcount
        assert len(networks.find_by(enabled=True)) >= 1
        assert 'CloudNetwork' in networks[0].type

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    def test_security_groups_query(self, cloud_provider, appliance):
        """Tests querying cloud networks subcollection for security groups info.

        Metadata:
            test_flag: rest
        """
        network = appliance.rest_api.collections.providers.get(
            name=cloud_provider.name).cloud_networks[0]
        network.reload(attributes='security_groups')
        security_groups = network.security_groups
        # "security_groups" needs to be present, even if it's just an empty list
        assert isinstance(security_groups, list)
        # if it's not empty, check type
        if security_groups:
            assert 'SecurityGroup' in security_groups[0]['type']

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    def test_create_arbitration_profiles(self, appliance, arbitration_profiles):
        """Tests creation of arbitration profiles.

        Metadata:
            test_flag: rest
        """
        for profile in arbitration_profiles:
            record = appliance.rest_api.collections.arbitration_profiles.get(id=profile.id)
            assert appliance.rest_api.response.status_code == 200
            assert record._data == profile._data
            assert 'ArbitrationProfile' in profile.type

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.parametrize('method', ['post', 'delete'])
    def test_delete_arbitration_profiles_from_detail(self, appliance, arbitration_profiles, method):
        """Tests delete arbitration profiles from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == 'delete' else 200
        for entity in arbitration_profiles:
            entity.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == status
            with error.expected('ActiveRecord::RecordNotFound'):
                entity.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    def test_delete_arbitration_profiles_from_collection(self, appliance, arbitration_profiles):
        """Tests delete arbitration profiles from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.arbitration_profiles
        collection.action.delete(*arbitration_profiles)
        assert appliance.rest_api.response.status_code == 200
        with error.expected('ActiveRecord::RecordNotFound'):
            collection.action.delete(*arbitration_profiles)
        assert appliance.rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_edit_arbitration_profiles(self, appliance, arbitration_profiles, from_detail):
        """Tests editing of arbitration profiles.

        Metadata:
            test_flag: rest
        """
        response_len = len(arbitration_profiles)
        zone = appliance.rest_api.collections.availability_zones[-1]
        locators = [{'id': zone.id}, {'href': zone.href}]
        new = [{'availability_zone': locators[i % 2]} for i in range(response_len)]
        if from_detail:
            edited = []
            for i in range(response_len):
                edited.append(arbitration_profiles[i].action.edit(**new[i]))
                assert appliance.rest_api.response.status_code == 200
        else:
            for i in range(response_len):
                new[i].update(arbitration_profiles[i]._ref_repr())
            edited = appliance.rest_api.collections.arbitration_profiles.action.edit(*new)
            assert appliance.rest_api.response.status_code == 200
        assert len(edited) == response_len
        for i in range(response_len):
            assert edited[i].availability_zone_id == zone.id

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_create_arbitration_rules_with_profile(self, request, appliance, arbitration_profiles):
        """Tests creation of arbitration rules referencing arbitration profiles.

        Metadata:
            test_flag: rest
        """
        num_rules = 2
        profile = arbitration_profiles[0]
        references = [{'id': profile.id}, {'href': profile._href}]
        data = []
        for index in range(num_rules):
            data.append({
                'description': 'test admin rule {}'.format(fauxfactory.gen_alphanumeric(5)),
                'operation': 'inject',
                'arbitration_profile': references[index % 2],
                'expression': {'EQUAL': {'field': 'User-userid', 'value': 'admin'}}
            })

        response = creating_skeleton(request, appliance.rest_api, 'arbitration_rules', data)
        assert appliance.rest_api.response.status_code == 200
        assert len(response) == num_rules
        for rule in response:
            record = appliance.rest_api.collections.arbitration_rules.get(id=rule.id)
            assert record.arbitration_profile_id == rule.arbitration_profile_id == profile.id

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_create_arbitration_rule_with_invalid_profile(self, request, appliance):
        """Tests creation of arbitration rule referencing invalid arbitration profile.

        Metadata:
            test_flag: rest
        """
        data = [{
            'description': 'test admin rule {}'.format(fauxfactory.gen_alphanumeric(5)),
            'operation': 'inject',
            'arbitration_profile': 'invalid_value',
            'expression': {'EQUAL': {'field': 'User-userid', 'value': 'admin'}}
        }]

        response = creating_skeleton(request, appliance.rest_api, 'arbitration_rules', data)
        # this will fail once BZ 1433477 is fixed - change and expand the test accordingly
        assert appliance.rest_api.response.status_code == 200
        for rule in response:
            assert not hasattr(rule, 'arbitration_profile_id')
