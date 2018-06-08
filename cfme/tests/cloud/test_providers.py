# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621
import uuid

import fauxfactory
import pytest
from widgetastic.exceptions import MoveTargetOutOfBoundsException

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.instance import Instance
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider, RHOSEndpoint
from cfme.common.provider_views import (
    CloudProviderAddView, CloudProvidersView, CloudProvidersDiscoverView)
from cfme.markers.env_markers.provider import ONE
from cfme.rest.gen_data import _creating_skeleton as creating_skeleton
from cfme.rest.gen_data import arbitration_profiles as _arbitration_profiles
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.providers import list_providers, ProviderFilter
from cfme.utils.rest import (
    assert_response,
    delete_resources_from_collection,
    delete_resources_from_detail,
)
from cfme.utils.update import update
from cfme.fixtures.provider import enable_provider_regions
from cfme.fixtures.pytest_store import store

pytestmark = [pytest.mark.provider([CloudProvider], scope="function")]


@pytest.fixture(scope='function')
def enable_regions(provider):
    enable_provider_regions(provider)


@pytest.mark.tier(3)
@test_requirements.discovery
@pytest.mark.uncollectif(lambda: store.current_appliance.version >= '5.9',
                         reason='no more support for cloud provider discovery')
def test_empty_discovery_form_validation_cloud(appliance):
    """ Tests that the flash message is correct when discovery form is empty."""
    collection = appliance.collections.cloud_providers

    collection.discover(None, AzureProvider)
    view = appliance.browser.create_view(CloudProvidersDiscoverView)
    view.flash.assert_message('Client ID, Client Key, Azure Tenant ID and '
                              'Subscription ID are required')


@pytest.mark.tier(3)
@test_requirements.discovery
@pytest.mark.uncollectif(lambda: store.current_appliance.version >= '5.9',
                         reason='no more support for cloud provider discovery')
def test_discovery_cancelled_validation_cloud(appliance):
    """ Tests that the flash message is correct when discovery is cancelled."""
    collection = appliance.collections.cloud_providers
    collection.discover(None, AzureProvider, cancel=True)
    view = appliance.browser.create_view(CloudProvidersView)
    view.flash.assert_success_message('Cloud Providers Discovery was cancelled by the user')


@pytest.mark.tier(3)
@test_requirements.discovery
def test_add_cancelled_validation_cloud(request, appliance):
    """Tests that the flash message is correct when add is cancelled."""
    collection = appliance.collections.cloud_providers
    prov = collection.instantiate(prov_class=EC2Provider)
    request.addfinalizer(prov.delete_if_exists)
    try:
        prov.create(cancel=True)
    except MoveTargetOutOfBoundsException:
        # TODO: Remove once fixed 1475303
        prov.create(cancel=True)
    view = prov.browser.create_view(CloudProvidersView)
    view.flash.assert_success_message('Add of Cloud Provider was cancelled by the user')


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda: store.current_appliance.version >= '5.9',
                         reason='no more support for cloud provider discovery')
def test_discovery_password_mismatch_validation_cloud(appliance):
    cred = Credential(
        principal=fauxfactory.gen_alphanumeric(5),
        secret=fauxfactory.gen_alphanumeric(5),
        verify_secret=fauxfactory.gen_alphanumeric(7))
    collection = appliance.collections.cloud_providers
    collection.discover(cred, EC2Provider)
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
    collection = appliance.collections.cloud_providers
    view = appliance.browser.create_view(CloudProvidersView)
    view.flash.assert_success_message('Amazon Cloud Providers: Discovery successfully initiated')
    collection.wait_for_new_provider()


@pytest.mark.uncollectif(lambda provider: (store.current_appliance.version >= '5.9' or
                                           not(provider.one_of(AzureProvider) or
                                               provider.one_of(EC2Provider))),
                         reason='no more support for cloud provider discovery')
@test_requirements.discovery
@pytest.mark.tier(1)
def test_providers_discovery(request, appliance, provider):
    """Tests provider discovery

    Metadata:
        test_flag: crud
    """
    if provider.one_of(AzureProvider):
        cred = Credential(
            principal=provider.default_endpoint.credentials.principal,
            secret=provider.default_endpoint.credentials.secret,
            tenant_id=provider.data['tenant_id'],
            subscription_id=provider.data['subscription_id'])
    elif provider.one_of(EC2Provider):
        cred = Credential(
            principal=provider.default_endpoint.credentials.principal,
            secret=provider.default_endpoint.credentials.secret,
            verify_secret=provider.default_endpoint.credentials.secret)

    collection = appliance.collections.cloud_providers

    collection.discover(cred, provider)
    view = provider.create_view(CloudProvidersView)
    view.flash.assert_success_message('Cloud Providers: Discovery successfully initiated')

    request.addfinalizer(CloudProvider.clear_providers)
    collection.wait_for_new_provider()


@pytest.mark.tier(3)
@pytest.mark.usefixtures('has_no_cloud_providers')
@test_requirements.discovery
def test_cloud_provider_add_with_bad_credentials(provider, enable_regions):
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

    with pytest.raises(Exception, match=flash):
        provider.create(validate_credentials=True)


@pytest.mark.tier(1)
@pytest.mark.smoke
@pytest.mark.usefixtures('has_no_cloud_providers')
@test_requirements.discovery
def test_cloud_provider_crud(provider, enable_regions):
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
def test_type_required_validation_cloud(request, appliance):
    """Test to validate type while adding a provider"""
    collection = appliance.collections.cloud_providers
    view = navigate_to(collection, 'Add')
    view.fill({'name': 'foo'})
    assert not view.add.active


@pytest.mark.tier(3)
@test_requirements.discovery
def test_name_required_validation_cloud(request, appliance):
    """Tests to validate the name while adding a provider"""
    collection = appliance.collections.cloud_providers
    prov = collection.instantiate(prov_class=EC2Provider,
                                  name=None,
                                  region='US East (Northern Virginia)')
    request.addfinalizer(prov.delete_if_exists)
    with pytest.raises(AssertionError):
        prov.create()
    view = prov.create_view(CloudProviderAddView)
    assert view.name.help_block == "Required"
    assert not view.add.active


@pytest.mark.tier(3)
def test_region_required_validation(request, soft_assert, appliance):
    """Tests to validate the region while adding a provider"""
    collection = appliance.collections.cloud_providers
    prov = collection.instantiate(prov_class=EC2Provider, name=fauxfactory.gen_alphanumeric(5),
                                  region=None)

    request.addfinalizer(prov.delete_if_exists)
    with pytest.raises(AssertionError):
        prov.create()
        view = prov.create_view(CloudProviderAddView)
        soft_assert(view.region.help_block == "Required")


@pytest.mark.tier(3)
@test_requirements.discovery
def test_host_name_required_validation_cloud(request, appliance):
    """Test to validate the hostname while adding a provider"""
    endpoint = RHOSEndpoint(hostname=None,
                            ip_address=fauxfactory.gen_ipaddr(prefix=[10]),
                            security_protocol=None)
    collection = appliance.collections.cloud_providers
    prov = collection.instantiate(prov_class=OpenStackProvider,
                                  name=fauxfactory.gen_alphanumeric(5),
                                  endpoints=endpoint)

    request.addfinalizer(prov.delete_if_exists)
    # It must raise an exception because it keeps on the form
    with pytest.raises(AssertionError):
        prov.create()
    endpoints = prov.create_view(prov.endpoints_form)
    assert endpoints.default.hostname.help_block == "Required"


@pytest.mark.tier(3)
def test_api_port_blank_validation(request, appliance):
    """Test to validate blank api port while adding a provider"""
    endpoint = RHOSEndpoint(hostname=fauxfactory.gen_alphanumeric(5),
                            ip_address=fauxfactory.gen_ipaddr(prefix=[10]),
                            api_port='',
                            security_protocol='Non-SSL')
    collection = appliance.collections.cloud_providers
    prov = collection.instantiate(prov_class=OpenStackProvider,
                                  name=fauxfactory.gen_alphanumeric(5),
                                  endpoints=endpoint)

    request.addfinalizer(prov.delete_if_exists)
    # It must raise an exception because it keeps on the form
    with pytest.raises(AssertionError):
        prov.create()
    endpoints = prov.create_view(prov.endpoints_form)
    assert endpoints.default.api_port.help_block == "Required"


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda: store.current_appliance.version >= '5.9',
                         reason='EC2 option not available')
def test_user_id_max_character_validation(appliance):
    cred = Credential(principal=fauxfactory.gen_alphanumeric(51), secret='')
    collection = appliance.collections.cloud_providers
    collection.discover(cred, EC2Provider)


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda: store.current_appliance.version >= '5.9',
                         reason='EC2 option not available')
def test_password_max_character_validation(appliance):
    password = fauxfactory.gen_alphanumeric(51)
    cred = Credential(
        principal=fauxfactory.gen_alphanumeric(5),
        secret=password,
        verify_secret=password)
    collection = appliance.collections.cloud_providers
    collection.discover(cred, EC2Provider)


@pytest.mark.tier(3)
@test_requirements.discovery
def test_name_max_character_validation_cloud(request, cloud_provider):
    """Test to validate that provider can have up to 255 characters in name"""
    request.addfinalizer(lambda: cloud_provider.delete_if_exists(cancel=False))
    name = fauxfactory.gen_alphanumeric(255)
    with update(cloud_provider):
        cloud_provider.name = name
    assert cloud_provider.exists


@pytest.mark.tier(3)
def test_hostname_max_character_validation_cloud(appliance):
    """Test to validate max character for hostname field"""
    endpoint = RHOSEndpoint(hostname=fauxfactory.gen_alphanumeric(256),
                            api_port=None,
                            security_protocol=None)
    collection = appliance.collections.cloud_providers
    prov = collection.instantiate(prov_class=OpenStackProvider,
                                  name=fauxfactory.gen_alphanumeric(5),
                                  endpoints=endpoint)
    try:
        prov.create()
    except MoveTargetOutOfBoundsException:
        # TODO: Remove once fixed 1475303
        prov.create()
    except AssertionError:
        endpoints = prov.create_view(prov.endpoints_form)
        assert endpoints.default.hostname.value == prov.hostname[0:255]


@pytest.mark.tier(3)
@test_requirements.discovery
def test_api_port_max_character_validation_cloud(appliance):
    """Test to validate max character for api port field"""
    endpoint = RHOSEndpoint(hostname=fauxfactory.gen_alphanumeric(5),
                            api_port=fauxfactory.gen_alphanumeric(16),
                            security_protocol='Non-SSL')
    collection = appliance.collections.cloud_providers
    prov = collection.instantiate(prov_class=OpenStackProvider,
                                  name=fauxfactory.gen_alphanumeric(5),
                                  endpoints=endpoint)
    try:
        prov.create()
    except AssertionError:
        view = prov.create_view(prov.endpoints_form)
        text = view.default.api_port.value
        assert text == prov.default_endpoint.api_port[0:15]


@pytest.mark.tier(2)
@pytest.mark.uncollectif(lambda provider: not provider.one_of(AzureProvider))
def test_azure_subscription_required(request, provider):
    """
    Tests that provider can't be added w/o subscription

    Metadata:
        test_flag: crud
    """
    provider.subscription_id = ''
    request.addfinalizer(provider.delete_if_exists)
    flash = ('Credential validation was not successful: '
            'Incorrect credentials - check your Azure Subscription ID')
    with pytest.raises(AssertionError, match=flash):
        provider.create()


@pytest.mark.tier(2)
@pytest.mark.usefixtures('has_no_cloud_providers')
def test_azure_multiple_subscription(appliance, request, soft_assert):
    """
    Verifies that different azure providers have different resources access

    Steps:
    1. Add all Azure providers
    2. Compare their VMs/Templates

    Metadata:
        test_flag: crud
    """
    pf = ProviderFilter(classes=[AzureProvider], required_flags=['crud'])
    providers = list_providers([pf])
    if len(providers) < 2:
        pytest.skip("this test needs at least 2 AzureProviders")
    prov_inventory = []
    for provider in providers:
        request.addfinalizer(provider.clear_providers)
        provider.create()
        provider.validate_stats()
        prov_inventory.append((provider.name,
                               provider.num_vm(),
                               provider.num_template()))

    for index, prov_a in enumerate(prov_inventory[:-1]):
        for prov_b in prov_inventory[index + 1:]:
            soft_assert(prov_a[1] != prov_b[1], "Same num_vms for {} and {}".format(prov_a[0],
                                                                               prov_b[0]))
            soft_assert(prov_a[2] != prov_b[2], "Same num_templates for {} and {}".format(prov_a[0],
                                                                                     prov_b[0]))


@pytest.mark.tier(3)
def test_openstack_provider_has_api_version(appliance):
    """Check whether the Keystone API version field is present for Openstack."""
    view = navigate_to(appliance.collections.cloud_providers, 'Add')
    view.fill({"prov_type": "OpenStack"})
    assert view.api_version.is_displayed, "API version select is not visible"


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda provider:
                         not provider.one_of(EC2Provider) or 'govcloud' in provider.data.tags)
def test_select_key_pair_none_while_provisioning(appliance, request, has_no_cloud_providers,
                                                 provider):
    """
        GH Issue: https://github.com/ManageIQ/manageiq/issues/10575

        Requirement: Have an ec2 provider with single key pair
                    (For now available in South America (Sao Paulo) region)
        1. Compute -> Cloud -> Instances
        2. Click on Provision Instances in Toolbar
        3. Go to Properties
        4. Select None in Guest Access Key Pair
        5. None should be selected
    """
    provider.region_name = 'South America (Sao Paulo)'
    request.addfinalizer(provider.delete_if_exists)

    provider.create()
    provider.validate()

    view = navigate_to(appliance.collections.cloud_instances, 'Provision')
    view.image_table[0].click()
    view.form.continue_button.click()

    view.form.properties.guest_keypair.fill('<None>')
    # check drop down was updated with selected value
    assert view.form.properties.guest_keypair.read() == '<None>'


@pytest.mark.tier(3)
def test_cloud_names_grid_floating_ips(appliance, ec2_provider, soft_assert):
    """
        Requirement: Cloud provider with floating IPs

        Go to Network -> Floating IPs
        Change view to grid
        Test if names are displayed
    """
    floating_ips_collection = appliance.collections.network_floating_ips
    view = navigate_to(floating_ips_collection, "All")
    view.toolbar.view_selector.select('Grid View')
    for entity in view.entities.get_all():
        if appliance.version < '5.9':
            soft_assert(entity.name)
        else:
            soft_assert('title="{}"'.format(entity.data['address']) in entity.data['quadicon'])


@pytest.mark.tier(3)
def test_display_network_topology(appliance, openstack_provider):
    """
        BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1343553

        Steps to Reproduce:
        1. Add RHOS undercloud provider
        2. Make sure it has no floating IPs
        3. Go to Networks -> Topology
        4. Topology should be shown without errors.
    """
    floating_ips_collection = appliance.collections.network_floating_ips
    view = navigate_to(floating_ips_collection, "All")
    if not view.entities.get_all():
        pytest.skip("No Floating IPs needed for this test")

    topology_col = appliance.collections.network_topology_elements
    view = navigate_to(topology_col, 'All')
    assert view.is_displayed
    view.flash.assert_no_error()


class TestProvidersRESTAPI(object):
    @pytest.fixture(scope="function")
    def arbitration_profiles(self, request, appliance, cloud_provider):
        num_profiles = 2
        response = _arbitration_profiles(
            request, appliance.rest_api, cloud_provider, num=num_profiles)
        assert_response(appliance)
        assert len(response) == num_profiles

        return response

    @pytest.mark.tier(3)
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
        assert_response(appliance)
        assert networks
        assert len(networks) == networks.subcount

        enabled_networks = 0
        networks.reload(expand=True)
        for network in networks:
            assert 'CloudNetwork' in network.type
            if network.enabled is True:
                enabled_networks += 1
        assert enabled_networks >= 1

    @pytest.mark.tier(3)
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
    # arbitration_profiles were removed in versions >= 5.9'
    @pytest.mark.uncollectif(lambda: store.current_appliance.version >= '5.9')
    def test_create_arbitration_profiles(self, appliance, arbitration_profiles):
        """Tests creation of arbitration profiles.

        Metadata:
            test_flag: rest
        """
        for profile in arbitration_profiles:
            record = appliance.rest_api.collections.arbitration_profiles.get(id=profile.id)
            assert_response(appliance)
            assert record._data == profile._data
            assert 'ArbitrationProfile' in profile.type

    @pytest.mark.tier(3)
    # arbitration_profiles were removed in versions >= 5.9'
    @pytest.mark.uncollectif(lambda: store.current_appliance.version >= '5.9')
    @pytest.mark.parametrize('method', ['post', 'delete'])
    def test_delete_arbitration_profiles_from_detail(self, arbitration_profiles, method):
        """Tests delete arbitration profiles from detail.

        Metadata:
            test_flag: rest
        """
        delete_resources_from_detail(arbitration_profiles, method=method)

    @pytest.mark.tier(3)
    # arbitration_profiles were removed in versions >= 5.9'
    @pytest.mark.uncollectif(lambda: store.current_appliance.version >= '5.9')
    def test_delete_arbitration_profiles_from_collection(self, arbitration_profiles):
        """Tests delete arbitration profiles from collection.

        Metadata:
            test_flag: rest
        """
        delete_resources_from_collection(arbitration_profiles)

    @pytest.mark.tier(3)
    # arbitration_profiles were removed in versions >= 5.9'
    @pytest.mark.uncollectif(lambda: store.current_appliance.version >= '5.9')
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
                assert_response(appliance)
        else:
            for i in range(response_len):
                new[i].update(arbitration_profiles[i]._ref_repr())
            edited = appliance.rest_api.collections.arbitration_profiles.action.edit(*new)
            assert_response(appliance)
        assert len(edited) == response_len
        for i in range(response_len):
            assert edited[i].availability_zone_id == zone.id

    @pytest.mark.tier(3)
    # arbitration_rules were removed in versions >= 5.9'
    @pytest.mark.uncollectif(lambda:
        store.current_appliance.version >= '5.9' or
        store.current_appliance.version < '5.8')
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
        assert_response(appliance)
        assert len(response) == num_rules
        for rule in response:
            record = appliance.rest_api.collections.arbitration_rules.get(id=rule.id)
            assert record.arbitration_profile_id == rule.arbitration_profile_id == profile.id

    @pytest.mark.tier(3)
    # arbitration_rules were removed in versions >= 5.9'
    @pytest.mark.uncollectif(lambda:
        store.current_appliance.version >= '5.9' or
        store.current_appliance.version < '5.8')
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
        assert_response(appliance)
        for rule in response:
            assert not hasattr(rule, 'arbitration_profile_id')


@pytest.mark.provider([CloudProvider], override=True, selector=ONE)
def test_tagvis_provision_fields(setup_provider, request, appliance, user_restricted, tag,
                                 soft_assert):
    """Test for network environment fields for restricted user"""
    image = appliance.collections.cloud_images.all()[0]
    image.add_tag(tag)
    request.addfinalizer(lambda: image.remove_tag(tag))
    with user_restricted:
        view = navigate_to(appliance.collections.cloud_instances, 'Provision')
        soft_assert(len(view.image_table.read()) == 1)
        view.image_table.row(name=image.name).click()
        view.form.continue_button.click()
        environment_fields_check = [view.form.environment.cloud_tenant,
                                    view.form.environment.availability_zone,
                                    view.form.environment.cloud_network,
                                    view.form.environment.security_groups,
                                    view.form.environment.public_ip_address,
                                    view.form.properties.guest_keypair]

        soft_assert(len(select) == 1 for select in environment_fields_check)
