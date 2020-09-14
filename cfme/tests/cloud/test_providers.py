import os
import uuid
from urllib.parse import urljoin

import fauxfactory
import pytest
from wait_for import wait_for
from widgetastic.exceptions import MoveTargetOutOfBoundsException
from widgetastic.widget import Text
from wrapanapi import VmState

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Endpoint
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.cloud.provider.openstack import RHOSEndpoint
from cfme.common.provider import prepare_endpoints
from cfme.common.provider_views import CloudProviderAddView
from cfme.common.provider_views import CloudProvidersView
from cfme.fixtures.provider import enable_provider_regions
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import SECOND
from cfme.utils import appliance
from cfme.utils import conf
from cfme.utils import ssh
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.generators import random_vm_name
from cfme.utils.log_validator import LogValidator
from cfme.utils.providers import get_crud
from cfme.utils.providers import list_providers
from cfme.utils.providers import ProviderFilter
from cfme.utils.rest import assert_response
from cfme.utils.update import update
from cfme.utils.wait import wait_for_decorator

pytestmark = [pytest.mark.provider([CloudProvider], scope="function")]

# path, where powershell scripts are located and where cfme image is downloaded,
# needed for test_create_azure_vm_from_azure_image
SPACE = '/mnt/space/'


@pytest.fixture(scope='function')
def enable_regions(provider):
    enable_provider_regions(provider)


@pytest.fixture(scope='function')
def az_pwsh_vm(appliance):
    """
    azure_pwsh contains powershell and necessary scripts to upload vhd, create VM, get ip of the
    resource and delete the VM.
    Find the provider that contains that template.

    The example of the configuration can be found in data/az_pwsh_cloudinit.cfg
    """
    filter_pwsh_template = ProviderFilter(required_fields=[['templates', 'powershell_vm']])
    providers = list_providers(filters=[filter_pwsh_template])
    if not providers:
        pytest.skip("There's no provider that contains a template with powershell")

    # If there's more than 1 provider that has the template, we select the first
    provider = providers[0]

    vm_name = random_vm_name(context="pwsh")
    pwsh_vm = provider.data.templates.powershell_vm.name

    collection = provider.appliance.provider_based_collection(provider)

    try:
        vm = collection.instantiate(vm_name, provider, pwsh_vm)
        vm.create_on_provider(allow_skip="default")
    except IndexError:
        from cfme.exceptions import ItemNotFound
        raise ItemNotFound('VM with powershell not found!')

    vm.mgmt.ensure_state(VmState.RUNNING)

    @wait_for_decorator(timeout="10m", delay=5)
    def get_ip_address():
        ip = vm.ip_address
        return ip is not None
    yield vm

    vm.cleanup_on_provider()


@pytest.fixture
def pwsh_ssh(az_pwsh_vm):
    """Provide vm_ssh_client for ssh operations in the test."""
    with ssh.SSHClient(hostname=az_pwsh_vm.ip_address,
                       username=credentials['host_default']['username'],
                       password=credentials['host_default']['password']) as vm_ssh_client:
        yield vm_ssh_client


@pytest.fixture
def connect_az_account(pwsh_ssh):
    """
    Connect to Azure account to run further scripts, see
    https://docs.microsoft.com/en-us/powershell/azure/authenticate-azureps
    """
    path_script = os.path.join(SPACE, 'connect_account.ps1')
    connect = pwsh_ssh.run_command(f"pwsh {path_script}", timeout=180)
    assert connect.success, "Failed to connect to Azure account"


@pytest.fixture(scope='function')
def cfme_vhd(appliance, pwsh_ssh):
    path_script = os.path.join(SPACE, 'get_ip.ps1')
    ip_of_recourse = pwsh_ssh.run_command(
        fr'pwsh {path_script}| grep -oE "([0-9]{{1,3}}\.){{3}}[0-9]{{1,3}}"',
        timeout=60).output.strip()
    if ip_of_recourse is not None:
        pytest.skip("The resource is taken by some other VM in Azure")
    stream = appliance.version.stream()
    try:
        # need to add the trailing slash for urljoin to work correctly
        url = '{}/'.format(conf.cfme_data['basic_info']['cfme_images_url'][stream])
    except KeyError:
        pytest.skip("Skipping since no such key found in yaml")

    image = pwsh_ssh.run_command(
        f"""wget -qO- {url} | grep -Po '(?<=href=")[^"]*' | grep azure""",
        timeout=30).output.strip()
    image_url = urljoin(url, image)
    pwsh_ssh.run_command(f"wget {image_url} -P {SPACE}",
                         timeout=180)

    # unpack the archive
    vhd = image.replace('zip', 'vhd')
    pwsh_ssh.run_command("unzip {} -d {}".format(os.path.join(SPACE, image), SPACE),
                         timeout=15 * 60)
    yield vhd

    pwsh_ssh.run_command("rm -f {}".format(os.path.join(SPACE, image)), timeout=180)
    pwsh_ssh.run_command("rm -f {}".format(os.path.join(SPACE, vhd)), timeout=180)


@pytest.fixture(scope='function')
def upload_image_to_azure(cfme_vhd, pwsh_ssh):
    path_script = os.path.join(SPACE, 'upload_vhd.ps1')
    pwsh_ssh.run_command(
        r"""sed -i '1s/.*/$BlobNameSource = "{vhd}"/' {script}"""
            .format(script=path_script, vhd=cfme_vhd), timeout=30)

    pwsh_ssh.run_command(f"pwsh {path_script}", timeout=15 * 60)


@pytest.fixture(scope='function')
def vm_ip(cfme_vhd, pwsh_ssh):
    # Create VM in Azure
    path_script = os.path.join(SPACE, 'create_vm.ps1')
    pwsh_ssh.run_command(
        r"""sed -i '1s/.*/$BlobNameSource = "{vhd}"/' {script} &&
        sed -i '2s/.*/$BlobNameDest = "{b_dest}"/' {script} &&
        sed -i '3s/.*/$VMName = "{name}"/' {script}""".format(
            script=path_script,
            vhd=cfme_vhd,
            b_dest=cfme_vhd.replace('azure', 'test'),
            name=cfme_vhd.replace('.x86_64.vhd', '-vm')),
        timeout=20)

    pwsh_ssh.run_command(f"pwsh {path_script}", timeout=600)

    # get the ip of the resource
    path_get_ip = os.path.join(SPACE, 'get_ip.ps1')
    ip = pwsh_ssh.run_command(
        fr'pwsh {path_get_ip}| grep -oE "([0-9]{{1,3}}\.){{3}}[0-9]{{1,3}}"',
        timeout=60).output.strip()
    yield ip

    # Delete the VM
    with pwsh_ssh:
        pwsh_ssh.run_command(
            r"""sed -i '1s/.*/$VMName = "{name}"/' {script}""".format(
                script=path_script,
                name=cfme_vhd.replace('.x86_64.vhd', '-vm')),
            timeout=20)

        pwsh_ssh.run_command(f"pwsh {path_script}", timeout=180)


@pytest.fixture
def instance_with_ssh_addition_template(appliance, provider):
    form_values = {'customize': {'custom_template': {'name': "SSH key addition template"}}}
    instance = appliance.collections.cloud_instances.create(random_vm_name('prov'), provider,
                                                            form_values=form_values)

    yield instance
    instance.delete()


@pytest.fixture
def stack_without_parameters(provider):
    stack = provider.mgmt.create_stack(name=fauxfactory.gen_alpha(10),
        template_url=provider.data.provisioning.stack_provisioning.template_without_parameters,
        capabilities=["CAPABILITY_IAM"])
    wait_for(lambda: stack.status_active, delay=15, timeout=900)

    yield stack
    stack.delete()


@pytest.fixture
def ec2_provider_with_sts_creds(appliance):
    collection = appliance.collections.cloud_providers
    prov = collection.instantiate(
        prov_class=EC2Provider, name=fauxfactory.gen_alphanumeric(5), key='ec2west'
    )
    assume_role_creds = prov.data.sts_assume_role.credentials
    creds = Credential(principal=credentials[assume_role_creds]['username'],
                       secret=credentials[assume_role_creds]['password'])
    endpoint = EC2Endpoint(
        assume_role_arn=prov.data.sts_assume_role.role_arn,
        credentials=creds)

    prov.endpoints = prepare_endpoints(endpoint)
    prov.region_name = prov.data.region_name

    yield prov
    prov.delete()


@pytest.fixture(params=["network_providers", "block_managers", "object_managers"])
def child_provider(request, appliance, provider):
    try:
        collection = getattr(appliance.collections, request.param).filter({"provider": provider})
    except AttributeError:
        pytest.skip(
            'Appliance collections did not include parametrized child provider type ({})'
            .format(request.param))
    yield collection.all()[0]


@pytest.mark.tier(3)
@test_requirements.discovery
def test_add_cancelled_validation_cloud(request, appliance):
    """Tests that the flash message is correct when add is cancelled.

    Polarion:
        assignee: pvala
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/16h
    """
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
@test_requirements.discovery
def test_cloud_provider_add_with_bad_credentials(
    request, provider, has_no_providers, enable_regions, appliance
):
    """ Tests provider add with bad credentials

    Metadata:
        test_flag: crud

    Polarion:
        assignee: pvala
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/6h
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
        for endp_name in list(provider.endpoints.keys()):
            if endp_name != 'default':
                del provider.endpoints[endp_name]

    @request.addfinalizer
    def clear_form():
        from cfme.common.provider_views import ProviderAddView
        view = appliance.browser.create_view(ProviderAddView)
        if view.is_displayed:
            view.cancel.click()
        assert not view.is_displayed

    with pytest.raises(Exception, match=flash):
        provider.create(validate_credentials=True)


@pytest.mark.tier(1)
@pytest.mark.smoke
@test_requirements.discovery
def test_cloud_provider_crud(provider, has_no_providers, enable_regions):
    """ Tests provider add with good credentials

    Metadata:
        test_flag: crud

    Polarion:
        assignee: pvala
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/3h
    """
    provider.create()
    provider.validate_stats(ui=True)

    old_name = provider.name
    with update(provider):
        provider.name = str(uuid.uuid4())  # random uuid

    with update(provider):
        provider.name = old_name  # old name

    provider.delete()
    provider.wait_for_delete()


@pytest.mark.tier(3)
@test_requirements.discovery
def test_type_required_validation_cloud(request, appliance):
    """Test to validate type while adding a provider

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/10h
    """
    collection = appliance.collections.cloud_providers
    view = navigate_to(collection, 'Add')
    view.fill({'name': 'foo'})
    assert not view.add.active


@pytest.mark.tier(3)
@test_requirements.discovery
def test_name_required_validation_cloud(request, appliance):
    """Tests to validate the name while adding a provider

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/15h
    """
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
    """Tests to validate the region while adding a provider

    Polarion:
        assignee: pvala
        caseimportance: low
        casecomponent: WebUI
        initialEstimate: 1/6h
    """
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
    """Test to validate the hostname while adding a provider

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/15h
    """
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
@test_requirements.general_ui
def test_api_port_blank_validation(request, appliance):
    """Test to validate blank api port while adding a provider

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/6h
    """
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
@test_requirements.discovery
def test_name_max_character_validation_cloud(request, cloud_provider):
    """Test to validate that provider can have up to 255 characters in name

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/15h
    """
    request.addfinalizer(lambda: cloud_provider.delete_if_exists(cancel=False))
    name = fauxfactory.gen_alphanumeric(255)
    with update(cloud_provider):
        cloud_provider.name = name
    assert cloud_provider.exists


@pytest.mark.tier(3)
def test_hostname_max_character_validation_cloud(appliance):
    """Test to validate max character for hostname field

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/15h
    """
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
    """Test to validate max character for api port field

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/15h
    """
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
@test_requirements.azure
@pytest.mark.provider([AzureProvider], scope="function")
def test_azure_subscription_required(request, provider):
    """
    Tests that provider can't be added w/o subscription

    Metadata:
        test_flag: crud

    Polarion:
        assignee: anikifor
        casecomponent: WebUI
        caseposneg: negative
        caseimportance: critical
        initialEstimate: 1/10h
        testSteps:
            1.Add Azure Provider w/0 subscription
            2.Validate
    """
    provider.subscription_id = ''
    request.addfinalizer(provider.delete_if_exists)
    with pytest.raises(AssertionError,
                       match='Credential validation was not successful: Incorrect credentials '
                             '- check your Azure Subscription ID'):
        provider.create()


@pytest.mark.tier(2)
@test_requirements.azure
@pytest.mark.provider([AzureProvider], scope="function", selector=ONE)
@pytest.mark.provider([AzureProvider], fixture_name="second_provider", selector=SECOND)
def test_azure_multiple_subscription(
        appliance, request, soft_assert, provider, second_provider, setup_provider
):
    """
    Verifies that different azure providers have different resources access

    Steps:
    1. Add all Azure providers
    2. Compare their VMs/Templates

    Metadata:
        test_flag: crud

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        initialEstimate: 1/4h
        caseimportance: critical
    """
    providers = [provider, second_provider]
    prov_inventory = []
    for provider in providers:
        request.addfinalizer(provider.clear_providers)
        provider.create(check_existing=True)
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
@test_requirements.azure
@pytest.mark.meta(automates=[1495318], blockers=[BZ(1756984)])
@pytest.mark.provider([AzureProvider], scope="function", selector=ONE)
def test_refresh_with_empty_iot_hub_azure(request, provider, setup_provider):
    """
    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: low
        initialEstimate: 1/6h
        setup: prepare env
               create an IoT Hub in Azure (using free tier pricing is good enough):
               $ az iot hub create --name rmanes-iothub --resource-group iot_rg
        testSteps:
            1. refresh azure provider
        expectedResults:
            1. no errors found in logs
    Bugzilla:
        1495318
    """
    result = LogValidator("/var/www/miq/vmdb/log/evm.log", failure_patterns=[r".*ERROR.*"])
    result.start_monitoring()
    azure = provider.mgmt
    if not azure.has_iothub():
        iothub_name = fauxfactory.gen_alpha(18, start="potatoiothub_")
        azure.create_iothub(iothub_name)
        request.addfinalizer(lambda: azure.delete_iothub(iothub_name))
        assert azure.has_iothub()
    provider.refresh_provider_relationships(wait=600)
    assert result.validate(wait="60s")


@test_requirements.azure
@pytest.mark.meta(automates=[1412363])
@pytest.mark.provider([AzureProvider], scope="function", selector=ONE)
@pytest.mark.tier(2)
def test_regions_gov_azure(provider):
    """
    This test verifies that Azure Government regions are not included in
    the default region list as most users will receive errors if they try
    to use them.
    Bugzilla:
        1412363

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
        setup: Check the region list when adding a Azure Provider.
        startsin: 5.7
    """
    view = navigate_to(AzureProvider, "Add")
    # prefill the provider type to enable regions dropdown
    view.fill({'prov_type': provider.type.capitalize()})
    available_regions = [opt.text for opt in view.region.all_options]
    # no government regions should be available by default
    assert not any(reg for reg in available_regions if 'gov' in reg.lower())


@test_requirements.general_ui
@pytest.mark.tier(3)
def test_openstack_provider_has_api_version(appliance):
    """Check whether the Keystone API version field is present for Openstack.

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        initialEstimate: 1/4h
    """
    view = navigate_to(appliance.collections.cloud_providers, 'Add')
    view.fill({"prov_type": "OpenStack"})
    assert view.api_version.is_displayed, "API version select is not visible"


def test_openstack_provider_has_dashboard(appliance, openstack_provider):
    """Check whether dashboard view is available for Openstack provider

    Bugzilla:
        1487142

    Polarion:
        assignee: pvala
        casecomponent: Cloud
        initialEstimate: 1/12h
        startsin: 5.10
    """
    view = navigate_to(openstack_provider, 'Details', use_resetter=False)
    view.toolbar.view_selector.select('Dashboard View')
    assert view.is_displayed


@test_requirements.ec2
@pytest.mark.tier(3)
@pytest.mark.provider([EC2Provider], scope="function")
def test_select_key_pair_none_while_provisioning(
    appliance, request, has_no_providers, provider
):
    """
        GH Issue: https://github.com/ManageIQ/manageiq/issues/10575

        Requirement: Have an ec2 provider with single key pair
                    (For now available in South America (Sao Paulo) region)
        1. Compute -> Cloud -> Instances
        2. Click on Provision Instances in Toolbar
        3. Go to Properties
        4. Select None in Guest Access Key Pair
        5. None should be selected

    Polarion:
        assignee: mmojzis
        casecomponent: WebUI
        initialEstimate: 1/4h
    """
    if 'govcloud' in provider.data.tags:
        pytest.skip("providers with such tag aren't supported for some reason")

    provider.region_name = 'South America (Sao Paulo)'
    request.addfinalizer(provider.delete_if_exists)

    provider.create()
    provider.validate()

    view = navigate_to(appliance.collections.cloud_instances, 'Provision', wait_for_view=0)
    view.image_table[0].click()
    view.form.continue_button.click()

    view.form.properties.guest_keypair.fill('<None>')
    # check drop down was updated with selected value
    assert view.form.properties.guest_keypair.read() == '<None>'


@pytest.mark.tier(3)
@test_requirements.azure
@pytest.mark.provider([AzureProvider])
def test_azure_instance_password_requirements(
    appliance, has_no_providers, setup_provider
):
    """
        Requirement: Have an Azure provider
        1. Compute -> Cloud -> Instances
        2. Click on Provision Instances in Toolbar
        3. Select template.
        4. Go to Customisation, fill password that doesn't match the criteria:
            * must be 12-72 characters
            * have 3 of the following - one lowercase character, one uppercase character,
              one number and one special character
        5. Error message should be displayed.

    Polarion:
        assignee: anikifor
        casecomponent: WebUI
        initialEstimate: 1/4h
    """
    view = navigate_to(appliance.collections.cloud_instances, 'Provision')
    view.image_table[0].click()
    view.form.continue_button.click()
    message = (
        "'Customize/Password' must be correctly formatted. The password must be 12-72 characters, "
        "and have 3 of the following - one lowercase character, one uppercase character, "
        "one number and one special character.")

    view.form.customize.fill({
        "admin_username": "some_value",
    })

    for pw in ("abcdefghijkl_",
               "ABCDEFGHIJKL_",
               "ABCDEFGHIJKLa",
               "abcdefgh_1A"):
        view.form.customize.fill({"root_password": pw})
        view.form.submit_button.click()
        wait_for(lambda: message in view.flash.read(),
                 fail_condition=False, num_sec=10, delay=.1)
        view.flash.dismiss()


@pytest.mark.tier(3)
@pytest.mark.provider([EC2Provider])
def test_cloud_names_grid_floating_ips(appliance, setup_provider, soft_assert):
    """
        Requirement: Cloud provider with floating IPs

        Go to Network -> Floating IPs
        Change view to grid
        Test if names are displayed

    Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: WebUI
        initialEstimate: 1/30h
    """
    floating_ips_collection = appliance.collections.network_floating_ips
    view = navigate_to(floating_ips_collection, "All")
    view.toolbar.view_selector.select('Grid View')
    for entity in view.entities.get_all():
        title = Text(
            view,
            f'//*[@id="miq-gtl-view"]//a[@title="{entity.data["address"]}"]'
        )
        soft_assert(title.is_displayed)


@test_requirements.general_ui
@pytest.mark.tier(3)
def test_display_network_topology(appliance, openstack_provider):
    """
    Bugzilla:
        1343553

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/8h
        testSteps:
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


@pytest.mark.provider([CloudProvider], scope='class')
class TestProvidersRESTAPI:
    @pytest.mark.tier(3)
    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_cloud_networks_query(self, provider, appliance, from_detail, setup_provider):
        """Tests querying cloud providers and cloud_networks collection for network info.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Cloud
            caseimportance: low
            initialEstimate: 1/3h
        """
        if from_detail:
            networks = provider.rest_api_entity.cloud_networks
        else:
            networks = appliance.rest_api.collections.cloud_networks
        assert_response(appliance)
        wait_for(
            lambda: len(networks) != 0,
            fail_func=provider.refresh_provider_relationships,
            timeout="40s",
            silent_failure=True,
        )
        assert len(networks) > 0, 'No cloud networks found'
        assert networks.name == 'cloud_networks'
        assert len(networks.all) == networks.subcount

        enabled_networks = 0
        networks.reload(expand=True)
        for network in networks:
            assert 'CloudNetwork' in network.type
            if network.enabled is True:
                enabled_networks += 1
        assert enabled_networks >= 1

    @pytest.mark.tier(3)
    def test_security_groups_query(self, provider, appliance, setup_provider):
        """Tests querying cloud networks subcollection for security groups info.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Cloud
            caseimportance: low
            initialEstimate: 1/4h
        """
        wait_for(
            lambda: len(provider.rest_api_entity.cloud_networks) != 0,
            fail_func=provider.refresh_provider_relationships,
            timeout="40s",
            silent_failure=True,
        )
        try:
            network = provider.rest_api_entity.cloud_networks[0]
        except IndexError:
            pytest.fail(f'No networks found on cloud provider {provider}')
        network.reload(attributes='security_groups')
        security_groups = network.security_groups
        # "security_groups" needs to be present, even if it's just an empty list
        assert isinstance(security_groups, list)
        # if it's not empty, check type
        if security_groups:
            assert 'SecurityGroup' in security_groups[0]['type']


@test_requirements.tag
@pytest.mark.provider([CloudProvider], selector=ONE)
def test_tagvis_provision_fields(setup_provider, request, appliance, user_restricted, tag,
                                 soft_assert):
    """Test for network environment fields for restricted user

    Polarion:
        assignee: prichard
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/3h
    """
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


@test_requirements.general_ui
@pytest.mark.tier(3)
@pytest.mark.provider([OpenStackProvider])
def test_domain_id_validation(request, provider):
    """ Test validating Keystone V3 needs domain_id

    prerequisites:
        * appliance

    Steps:
        * Navigate add Cloud provider and select OpenStack
        * Select Keystone V3 as API Version
        * Validate without Domain ID

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        initialEstimate: 1/4h
    """
    prov = provider
    prov.api_version = 'Keystone v3'
    prov.keystone_v3_domain_id = None
    request.addfinalizer(prov.delete_if_exists)
    # It must raise an exception because it keeps on the form
    with pytest.raises(AssertionError):
        prov.create()
    view = prov.create_view(CloudProviderAddView)

    # ToDo: Assert proper flash message after BZ-1545520 fix.
    assert view.flash[0].type == 'error'


@test_requirements.azure
@pytest.mark.meta(automates=[1315945])
@pytest.mark.provider([AzureProvider], selector=ONE)
def test_vpc_env_selection(setup_provider, request, provider, appliance, provisioning):
    """
    Test selection of components in environment page of cloud instances
    with selected virtual private cloud

    Polarion:
        assignee: anikifor
        casecomponent: WebUI
        initialEstimate: 1/2h
        testSteps:
            1. Provision an Azure Instance from an Image.
            2. At the environment page, try to select components with vpc
        expectedResults:
            1. Instance provisioned and added successfully
            2. Items are selected successfully

    Bugzilla:
        1315945
    """
    vm_name = random_vm_name('prov-az')
    template = provisioning.get('image').get('name')
    vm = appliance.collections.cloud_instances.instantiate(name=vm_name,
                                                           provider=provider,
                                                           template_name=template)
    request.addfinalizer(vm.cleanup_on_provider)
    # default args select vpc
    data = vm.vm_default_args
    data['template_name'] = template
    data['provider_name'] = provider.name
    view = navigate_to(vm.parent, 'Provision')
    view.form.fill_with(data, on_change=view.form.submit_button)
    view.flash.assert_no_error()

    # make sure the request succeeds
    request_description = f'Provision from [{template}] to [{vm_name}]'
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui', num_sec=15 * 60)
    assert provision_request.is_succeeded(method='ui'), "Provisioning failed: {}".format(
        provision_request.row.last_message.text)


@pytest.mark.manual
@test_requirements.azure
@pytest.mark.tier(1)
def test_sdn_nsg_arrays_refresh_azure():
    """
    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
            1. Add Network Security group on Azure with coma separated port ranges
            `1023,1025` rule inbound/outbound ( ATM this feature is not allowed in
            East US region of Azure - try West/Central)
            2. Add such Azure Region into CFME
            3. Refresh provider
        expectedResults:
            1. The group is successfully added
            2. The region is successfully added
            3. Refreshed succesfully, there are no errors in the logs

    Bugzilla:
        1520196
    """
    pass


@pytest.mark.manual
@test_requirements.azure
@pytest.mark.tier(2)
def test_provider_flavors_azure():
    """
    Verify that the vm flavors in Azure are of the correct sizes and that
    the size display in CFME is accurate.
    Low priority as it is unlikely to change once set.  Will want to check
    when azure adds new sizes.  Only need to spot check a few values.
    For current size values, you can check here:
    https://docs.microsoft.com/en-us/azure/virtual-machines/linux/sizes

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: low
        initialEstimate: 1/8h
        startsin: 5.6
        testSteps:
            1. Add Azure provider
            2. Navigate to Flavours
        expectedResults:
            1. The provider is successfully added
            2. Flavours are the same as in MS documentation
    Bugzilla:
        1357086
    """
    pass


@pytest.mark.manual
@test_requirements.azure
@pytest.mark.tier(1)
def test_market_place_images_azure():
    """
    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
            1.Enable market place images
            2.Add Azure provider
            3.Refresh the provider
        expectedResults:
            1.
            2.
            3. Refresh is done fast (faster than 15 minutes)
    Bugzilla:
        1491330
    """
    pass


@pytest.mark.ignore_stream('5.11')
@test_requirements.azure
@pytest.mark.tier(1)
def test_create_azure_vm_from_azure_image(connect_az_account, cfme_vhd, upload_image_to_azure,
                                          vm_ip):
    """
    To run this test Azure account is required.

    Azure VM is provisioned from another VM using Powershell, that can be run on any provider.

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/2h
        setup: # Virtual Machine Name - as it appears in Azure
               $VMName = "myVmName"
               $ResourceGroupName = "CFMEQE-Main"
               Break
               # Existing Azure Deployment Values - Video with instructions
               forthcoming.
               $AvailabilitySetName = "cfmeqe-as-free"
               $AzureLocation = "East US"
               $VMDeploymentSize= "Standard_A1"
               $StorageAccountName = "cfmeqestore"
               $BlobContainerName = "templates"
               $VHDName = "cfme-azure-56013.vhd"
               $VirtualNetworkName = "cfmeqe"
               $NetworkSecurityGroupName = "cfmeqe-nsg"
               $VirtualNetworkSubnetName = "default"
               $VirtualNetworkAddressPrefix = "10.0.0.0/16"
               $VirtualNetworkSubnetAddressPrefix = "10.0.0.0/24"
               # Create VM Components
               $StorageAccount = Get-AzureRmStorageAccount -ResourceGroupName
               $ResourceGroupName -Name $StorageAccountName
               $InterfaceName = $VMName
               $NetworkSecurityGroupID = Get-AzureRmNetworkSecurityGroup -Name
               $NetworkSecurityGroupName -ResourceGroupName $ResourceGroupName
               $PIp = New-AzureRmPublicIpAddress -Name $InterfaceName
               -ResourceGroupName $ResourceGroupName -Location $AzureLocation
               -AllocationMethod Dynamic -Force
               $SubnetConfig = New-AzureRmVirtualNetworkSubnetConfig -Name
               $VirtualNetworkSubnetName -AddressPrefix
               $VirtualNetworkSubnetAddressPrefix
               $VNet = New-AzureRmVirtualNetwork -Name $VirtualNetworkName
               -ResourceGroupName $ResourceGroupName -Location $AzureLocation
               -AddressPrefix $VirtualNetworkAddressPrefix -Subnet $SubnetConfig
               -Force
               $Interface = New-AzureRmNetworkInterface -Name $InterfaceName
               -ResourceGroupName $ResourceGroupName -Location $AzureLocation
               -SubnetId $VNet.Subnets[0].Id -PublicIpAddressId $PIp.Id -Force
               $AvailabilitySet = Get-AzureRmAvailabilitySet -ResourceGroupName
               $ResourceGroupName -Name $AvailabilitySetName
               $VirtualMachine = New-AzureRmVMConfig -VMName $VMName -VMSize
               $VMDeploymentSize -AvailabilitySetID $AvailabilitySet.Id
               $VirtualMachine = Add-AzureRmVMNetworkInterface -VM $VirtualMachine
               -Id $Interface.Id
               $OSDiskUri = $StorageAccount.PrimaryEndpoints.Blob.ToString() +
               $BlobContainerName + "/" + $VHDName
               $VirtualMachine = Set-AzureRmVMOSDisk -VM $VirtualMachine -Name
               $VMName -VhdUri $OSDiskUri -CreateOption attach -Linux
               # Create the Virtual Machine
               New-AzureRmVM -ResourceGroupName $ResourceGroupName -Location
               $AzureLocation -VM $VirtualMachine
        testSteps:
            1. Make the VM
            2. Config SSH support
            3. Config DNS is desired.
            4. SSH into new VM with Azure Public IP address and verify it has booted
            correctly.
            5. Use HTTP to DNS into the appliance web ui and make sure
            you can log in.
        startsin: 5.6
        teardown: When you"re done, delete everything.  Make sure at a minimum that the
                  VM is completely Stopped in Azure.
    """
    app = appliance.IPAppliance.from_url(vm_ip)

    # Credentials for the provisioned VM from CFME image, this is different to the VM that runs
    # powershell scripts as Azure has specific requirements for login/password.
    # These credentials are used in the script create_vm.ps1 to provision the VM.
    username = credentials['azure_appliance']['username']
    password = credentials['azure_appliance']['password']

    with ssh.SSHClient(hostname=vm_ip,
                       username=username,
                       password=password) as app_ssh_client:

        # permit root login over ssh for future appliance configuration
        command = 'sed -i "s/.*PermitRootLogin.*/PermitRootLogin yes/g" /etc/ssh/sshd_config'
        config = app_ssh_client.run_command(
            f'echo {password} | sudo -S {command}', ensure_user=True)
        assert config.success

        # restart sshd to apply configuration changes
        restart = app_ssh_client.run_command(
            f'echo {password} | sudo -S systemctl restart sshd', ensure_user=True)
        assert restart.success

        # unlock root password
        unlock = app_ssh_client.run_command(
            f'echo {password} | sudo -S passwd -u root', ensure_user=True)
        assert unlock.success

    app.configure()
    app.wait_for_miq_ready()

    # Check we can login
    logged_in_page = app.server.login()
    assert logged_in_page.is_displayed


@test_requirements.ec2
@pytest.mark.provider([EC2Provider], scope="function", selector=ONE)
def test_refresh_with_stack_without_parameters(
    provider, has_no_providers, request, stack_without_parameters
):
    """
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/5h
        testSteps:
            1. Add cloudformation stack without parameters(https://s3-us-
            west-2.amazonaws.com/cloudformation-templates-us-
            west-2/Managed_EC2_Batch_Environment.template  )
            2. Add ec2 provider with cloudformation stack without parameters
        expectedResults:
            1.
            2. Wait for refresh - it should be refreshed successfully without errors
    """
    provider.create()
    request.addfinalizer(provider.delete_if_exists)
    provider.refresh_provider_relationships()
    provider.validate_stats(ui=True)


@test_requirements.cloud
@pytest.mark.long_running
@pytest.mark.ignore_stream("5.10", "5.11")
@pytest.mark.meta(automates=[1491330, 1612086])
@pytest.mark.provider([AzureProvider, EC2Provider], scope="function")
def test_public_images_enable_disable(setup_provider, request, appliance, provider):
    """
    Bugzilla:
        1491330
        1612086
    The easiest way to simulate AWS API Limit for > 200 items is to enable
    and disable public images.
    So test for testing public images and for testing AWS API Limit is combined in this test.
    Polarion:
        assignee: mmojzis
        caseimportance: critical
        initialEstimate: 1 1/2h
        casecomponent: Cloud
        testSteps:
            1. Enable public images for ec2
            2. Add ec2 provider
            3. Wait for its refresh(It can take more than 30 minutes)
            4. Disable public images for ec2
            5. Wait for its refresh(It can take more than 30 minutes)
        expectedResults:
            1.
            2.
            3. Refresh should be successful and public images collected
            4.
            5. Refresh should be successful and public images uncollected
    """
    # if provider gets stuck loading images it could take more than two hours to be in operating
    # state which can cause other test to fail so better to delete provider for safety
    request.addfinalizer(lambda: provider.delete_if_exists())
    request.addfinalizer(lambda: appliance.set_public_images(provider, enabled=False))
    # enable
    public_provider_images_min = 20000 if provider.one_of(AzureProvider) else 40000
    private_provider_images_max = 5000
    appliance.set_public_images(provider, enabled=True)
    provider.refresh_provider_relationships(method='ui')
    wait_for(lambda: int(provider.load_details(refresh=True).entities.summary("Relationships")
        .get_text_of("Images")) > public_provider_images_min, delay=120, timeout=3600 * 3)
    # disable
    appliance.set_public_images(provider, enabled=False)
    provider.refresh_provider_relationships(method='ui')
    wait_for(lambda: int(provider.load_details(refresh=True).entities.summary("Relationships")
        .get_text_of("Images")) < private_provider_images_max, delay=120, timeout=3600 * 3)


@test_requirements.ec2
@pytest.mark.provider([EC2Provider], scope="function", selector=ONE)
def test_create_sns_topic(has_no_providers, provider, request):
    """
    Requires: No SNS topic(AWS_Config) for tested region

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
        testSteps:
            1. Add an ec2 provider with tested region
            2. Wait 3 minutes
        expectedResults:
            1.
            2. Check SNS topic exists for this region in AWS
    """
    # preparations for test
    request.addfinalizer(provider.delete_if_exists)
    topic = provider.mgmt.get_arn_if_topic_exists('AWSConfig_topic')
    if topic:
        provider.mgmt.delete_topic(topic)

    # SNS topic should be automatically created during provider creation in CFME
    provider.create()
    new_topic = wait_for(lambda: provider.mgmt.get_arn_if_topic_exists('AWSConfig_topic'), delay=15,
                         timeout=300)

    # set topic targets in the environment so refreshes run correctly
    provider.mgmt.set_sns_topic_target_for_all_cw_rules(new_topic)


@test_requirements.ec2
@pytest.mark.provider([EC2Provider], scope="function", selector=ONE)
def test_add_delete_add_provider(setup_provider, provider, request):
    """
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1h
        caseimportance: critical
        testSteps:
            1. Add ec2 provider
            2. Delete ec2 provider
            3. Add ec2 provider
        expectedResults:
            1.
            2.
            3. Ec2 provider should be successfully added again without any issues
    """
    provider.delete()
    provider.create()
    request.addfinalizer(provider.delete_if_exists)
    provider.refresh_provider_relationships()
    provider.validate_stats(ui=True)


@test_requirements.ec2
@pytest.mark.provider([EC2Provider], scope="function", selector=ONE)
def test_deploy_instance_with_ssh_addition_template(setup_provider,
                                                    instance_with_ssh_addition_template):
    """
    Requirement: EC2 provider

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
            1. Provision an instance
            2. Select Choose Automatically in Environment -> Placement
            3. Select SSH key addition template in Customize -> Customize Template
            4. Provision instance
        expectedResults:
            1.
            2.
            3.
            4. Instance should be provisioned without any errors
    """
    if not instance_with_ssh_addition_template.exists:
        pytest.fail('Instance with ssh addition template was not created successfully!')


@test_requirements.ec2
@pytest.mark.manual
def test_add_ec2_provider_with_instance_without_name():
    """
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/6h
        testSteps:
            1. Add an ec2 provider with instance without name
            2. Wait for refresh
        expectedResults:
            1.
            2. Refresh should complete without errors
    """
    pass


@pytest.mark.provider([EC2Provider], scope="function", selector=ONE)
@test_requirements.ec2
def test_regions_up_to_date(provider):
    """
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/3h
        testSteps:
            1. Compare regions in AWS Console with regions for EC2 in CFME
        expectedResults:
            1. There should be same regions in CFME as in AWS Console.
    """
    regions_provider = provider.mgmt.list_regions(verbose=True)
    view = navigate_to(CloudProvider, 'Add')
    view.prov_type.fill("Amazon EC2")
    regions_cfme = view.region.all_options
    # Delete option <Choose>
    regions_cfme.pop(0)
    regions_cfme_texts = [option.text for option in regions_cfme]
    # fixing recent change in AWS naming from EU to Europe:
    regions_cfme_texts = [region.replace('EU', 'Europe') for region in regions_cfme_texts]
    regions_not_in_cfme = set(regions_provider) - set(regions_cfme_texts)
    extra_regions_in_cfme = set(regions_cfme_texts) - set(regions_provider)
    if len(regions_not_in_cfme) > 0:
        pytest.fail(f"Regions {regions_not_in_cfme} are not in CFME!")
    if len(extra_regions_in_cfme) > 0:
        pytest.fail(f"Extra regions in CFME: {extra_regions_in_cfme}")


@test_requirements.ec2
@pytest.mark.manual
def test_add_ec2_provider_with_non_default_url_endpoint():
    """
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/6h
        testSteps:
            1. Add an ec2 provider with non default url endpoint
            2. Wait for refresh
        expectedResults:
            1. Provider should be added with no issues
            2. Refresh should complete without errors
    """
    pass


@test_requirements.ec2
@pytest.mark.ignore_stream("5.10")
def test_add_ec2_provider_with_sts_assume_role(appliance, ec2_provider_with_sts_creds):
    """
    Requires:
        The requirement is only on EC2 side and needs to be added manually once.
        1. Role which has all the required permissions to manage CFME
        2. Edit Trust relationship policy for this role to:
            {
              "Version": "2012-10-17",
              "Statement": [
                {
                  "Effect": "Allow",
                  "Principal": {
                    "AWS": "arn:aws:iam::NNNNNNNNNNNN:root"
                  },
                  "Action": "sts:AssumeRole"
                }
              ]
            }
        3. Have policy with AssumeRole permission:
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "sts:AssumeRole",
                        "Resource": "arn:aws:iam::NNNNNNNNNNNN:role/RoleForCFME"
                    }
                ]
            }
        4. Have an user with only attached policy created in last step

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/2h
        caseimportance: high
        casecomponent: Cloud
        testSteps:
            1. Go to Compute -> Cloud -> Providers
            2. Add EC2 Provider with these fields filled in:
        expectedResults:
            1.
            2. Provider should be successfully added.
    """
    ec2_provider_with_sts_creds.create()
    ec2_provider_with_sts_creds.validate()


@test_requirements.ec2
@pytest.mark.meta(automates=[1658207])
@pytest.mark.provider([EC2Provider], scope="function", selector=ONE)
def test_add_second_provider(setup_provider, provider, request):
    """
        Bugzilla: 1658207

        Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/3h
        caseimportance: high
        casecomponent: Cloud
        testSteps:
            1. Go to Compute -> Cloud -> Providers
            2. Add EC2 Provider
            3. Add another EC2 Provider
        expectedResults:
            1.
            2. Provider should be successfully added.
            3. Provider should be successfully added.
    """
    second_provider = get_crud(provider.key)
    second_provider.name = f"{provider.name}-2"
    second_provider.create()
    request.addfinalizer(second_provider.delete_if_exists)
    second_provider.refresh_provider_relationships()
    second_provider.validate_stats(ui=True)
    assert provider.exists and second_provider.exists


@test_requirements.ec2
@pytest.mark.meta(automates=[1710599, 1710623])
@pytest.mark.ignore_stream("5.10")  # BZ 1710623 was not merged into 5.10
def test_provider_compare_ec2_provider_and_backup_regions(appliance):
    """
    Bugzilla:
        1710599
        1710623
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/6h
        caseimportance: medium
        casecomponent: Cloud
        testSteps:
            1. Go to Compute -> Cloud -> Providers -> Add a new Cloud Provider
            2. Select Provider: Amazon EC2 and list AWS Regions
            3. Go to Configuration -> Settings -> Schedules -> Add a new Schedule
            4. Select Action: Database Backup, Type: AWS S3 and list AWS Regions
            5. Go to Configuration -> Diagnostics -> Region -> Database
            6. Select Type: AWS S3 and list AWS Regions
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. Compare all three lists. They should contain same regions.
    """
    view = navigate_to(CloudProvider, 'Add')
    view.prov_type.fill("Amazon EC2")
    regions_provider_texts = [option.text for option in view.region.all_options if
                              option.text != "<Choose>"]
    regions_provider_texts.sort()

    view = navigate_to(appliance.collections.system_schedules, 'Add')
    view.form.action_type.fill("Database Backup")
    view.form.database_backup.backup_type.fill("AWS S3")
    regions_scheduled_backup = view.form.database_backup.backup_settings.aws_region.all_options
    regions_scheduled_backup_texts = [option.text for option in regions_scheduled_backup if
                                      option.text != "<Choose>"]
    regions_scheduled_backup_texts.sort()

    view = navigate_to(appliance.server.zone.region, 'Database')
    view.db_backup_settings.backup_type.fill("AWS S3")
    regions_immediate_backup = view.db_backup_settings.backup_settings.aws_region.all_options
    regions_immediate_backup_texts = [option.text for option in regions_immediate_backup if
                                      option.text != "<Choose>"]
    regions_immediate_backup_texts.sort()

    assert regions_provider_texts == regions_scheduled_backup_texts
    assert regions_provider_texts == regions_immediate_backup_texts


@test_requirements.cloud
@pytest.mark.meta(automates=[1632750], blockers=[BZ(1632750,
                                                 unblock=lambda child_provider: "object_managers"
                                                 in child_provider)])
@pytest.mark.uncollectif(lambda child_provider, provider:
                        (provider.one_of(EC2Provider) and (child_provider == "object_managers")) or
                        (provider.one_of(AzureProvider) and (child_provider !=
                                                             'network_providers')),
                        reason="Storage is not supported by AzureProvider "
                               "and Object Storage is not supported by EC2Provider")
@test_requirements.cloud
@pytest.mark.provider([AzureProvider, EC2Provider, OpenStackProvider], scope="function")
def test_cloud_provider_dashboard_after_child_provider_remove(
        appliance, provider, request, setup_provider_funcscope, child_provider):
    """
        Bugzilla: 1632750

        Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/6h
        caseimportance: high
        casecomponent: Cloud
        testSteps:
            1. Have a cloud provider added
            2. Delete one of its child managers
            3. Go to cloud provider Dashboard
        expectedResults:
            1.
            2.
            3. Dashboard should load without any issues
    """
    child_provider.delete(cancel=False)

    # Sometimes provider was not deleted so this preventing to use provider without child providers
    # to be used in next tests
    @request.addfinalizer
    def _wait_for_delete_provider():
        provider.delete()
        provider.wait_for_delete()

    view = navigate_to(provider, "Details")
    view.toolbar.view_selector.select('Dashboard View')
    view.wait_displayed()
    view.flash.assert_no_error()
