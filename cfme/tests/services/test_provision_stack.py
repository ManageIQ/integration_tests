import re

import fauxfactory
import pytest
from wait_for import wait_for

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import providers
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.datafile import load_data_file
from cfme.utils.log_validator import LogValidator
from cfme.utils.path import orchestration_path
from cfme.utils.providers import ProviderFilter

filter_kwargs = {
    'required_fields': [['provisioning', 'stack_provisioning']],
}

cloud_filter = ProviderFilter(classes=[CloudProvider], **filter_kwargs)
not_ec2 = ProviderFilter(classes=[EC2Provider], inverted=True)

pytestmark = [
    pytest.mark.meta(server_roles='+automate'),
    pytest.mark.ignore_stream('upstream'),
    test_requirements.stack,
    pytest.mark.tier(2),
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider(gen_func=providers,
                         filters=[cloud_filter],
                         selector=ONE_PER_TYPE,
                         scope='module'),
]


@pytest.fixture
def stack_data(appliance, provider, provisioning, request):
    random_base = fauxfactory.gen_alphanumeric()
    stackname = f'test{random_base}'
    vm_name = f'test-{random_base}'
    stack_timeout = '20'
    if provider.one_of(AzureProvider):
        try:
            template = provider.data.templates.small_template
            vm_user = credentials[template.creds].username
            vm_password = credentials[template.creds].password
        except AttributeError:
            pytest.skip(f'Could not find small_template or credentials for {provider.name}')

        stack_data = {
            'stack_name': stackname,
            'resource_group': provisioning.get('resource_group'),
            'deploy_mode': provisioning.get('mode'),
            'location': provisioning.get('region_api'),
            'vmname': vm_name,
            'vmuser': vm_user,
            'vmpassword': vm_password,
            'vmsize': provisioning.get('vm_size'),
            'cloudnetwork': provisioning.get('cloud_network').split()[0],
            'cloudsubnet': provisioning.get('cloud_subnet').split()[0]
        }
        if "test_error_message_azure" in request.node.name:  # for this test the bad pass is needed
            stack_data['vmpassword'] = 'test'
    elif provider.one_of(OpenStackProvider):
        stack_prov = provisioning['stack_provisioning']
        stack_data = {
            'stack_name': stackname,
            'key': stack_prov['key_name'],
            'flavor': stack_prov['instance_type'],
            'tenant_name': provisioning['cloud_tenant'],
            'private_network': provisioning['cloud_network']
        }
    else:
        stack_prov = provisioning['stack_provisioning']
        stack_data = {
            'stack_name': stackname,
            'stack_timeout': stack_timeout,
            'param_virtualMachineName': vm_name,
            'param_KeyName': stack_prov['key_name']
        }
    return stack_data


@pytest.fixture
def dialog_name():
    return fauxfactory.gen_alphanumeric(12, start="dialog_")


@pytest.fixture
def template(appliance, provider, provisioning, dialog_name):
    template_group = provisioning['stack_provisioning']['template_type']
    template_type = provisioning['stack_provisioning']['template_type_dd']
    template_name = fauxfactory.gen_alphanumeric(start="temp_")
    file = provisioning['stack_provisioning']['data_file']
    data_file = load_data_file(str(orchestration_path.join(file)))
    content = data_file.read().replace('CFMETemplateName', template_name)
    collection = appliance.collections.orchestration_templates
    template = collection.create(template_group=template_group, template_name=template_name,
                                 template_type=template_type, description="my template",
                                 content=content)
    template.create_service_dialog_from_template(dialog_name)
    yield template
    if template.exists:
        template.delete()


@pytest.fixture
def catalog(appliance):
    cat_name = fauxfactory.gen_alphanumeric(start="cat_")
    catalog = appliance.collections.catalogs.create(name=cat_name, description="my catalog")
    yield catalog
    if catalog.exists:
        catalog.delete()


@pytest.fixture
def catalog_item(appliance, dialog, catalog, template, provider, dialog_name):
    item_name = fauxfactory.gen_alphanumeric(15, start="cat_item_")
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.ORCHESTRATION,
        name=item_name,
        description="my catalog",
        display_in=True,
        catalog=catalog,
        dialog=dialog_name,
        orch_template=template,
        provider_name=provider.name,
    )
    yield catalog_item
    if catalog_item.exists:
        catalog_item.delete()


@pytest.fixture
def service_catalogs(appliance, catalog_item, stack_data):
    return ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name, stack_data)


@pytest.fixture
def stack_created(appliance, provider, order_stack, stack_data):
    provision_request = order_stack
    provision_request.wait_for_request(method='ui')
    assert provision_request.is_succeeded()
    stack = appliance.collections.cloud_stacks.instantiate(stack_data['stack_name'],
                                                           provider=provider)
    stack.wait_for_exists()
    yield stack


@pytest.fixture
def order_stack(appliance, provider, stack_data, service_catalogs):
    """Fixture which prepares provisioned stack"""
    provision_request = service_catalogs.order()
    stack = appliance.collections.cloud_stacks.instantiate(stack_data['stack_name'],
                                                           provider=provider)
    yield provision_request
    prov_req_cleanup(appliance, provision_request)
    if stack.delete_if_exists():
        stack.wait_for_not_exists()


def guess_svc_name(provision_request):
    matchpairs = [
        ('description', r'\[EVM\] Service \[([\w-]+)\].*'),
        ('message', r'\[EVM\] Service \[([\w-]+)\].*'),
        ('message', r'Server \[EVM\] Service \[([\w-]+)\].*')
    ]

    for attr, pattern in matchpairs:
        text = getattr(provision_request, attr)
        match = re.match(pattern, text)
        if match:
            return match.group(1)
    return None


def prov_req_cleanup(appliance, provision_request):
    provision_request.update()
    svc_name = wait_for(
        func=guess_svc_name,
        func_args=(provision_request,),
        fail_func=provision_request.update,
        fail_condition=None,
        timeout='5m').out

    myservice = MyService(appliance, name=svc_name)
    svc_cleanup(myservice)


def svc_cleanup(service):
    # I think we do not really want conditional cleanups here -- to issue
    # delete only if service exists. The service name can be guessed wrong. In
    # that case we would not do cleanup as the `exists` returns false and
    # the provider gets one more item of orphaned junk.
    service.retire()
    service.delete()


@test_requirements.provision
def test_provision_stack(order_stack, stack_created):
    """Tests stack provisioning

    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
        initialEstimate: 1/3h
        casecomponent: Provisioning
    """
    provision_request = order_stack
    assert provision_request.is_succeeded()
    assert stack_created.exists


@pytest.mark.meta(blockers=[BZ(1754543)])
def test_reconfigure_service(appliance, service_catalogs, request):
    """Tests service reconfiguring

    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: stack
    """
    provision_request = service_catalogs.order()
    provision_request.wait_for_request(method='ui')
    last_message = provision_request.get_request_row_from_ui()['Last Message'].text
    service_name = last_message.split()[2].strip('[]')
    myservice = MyService(appliance, service_name)
    request.addfinalizer(lambda: svc_cleanup(myservice))
    assert provision_request.is_succeeded()
    myservice.reconfigure_service()


# EC2 locks template between Stack order and template removal'
@pytest.mark.provider(gen_func=providers,
                      filters=[cloud_filter, not_ec2],
                      selector=ONE_PER_TYPE,
                      scope='module')
def test_remove_non_read_only_orch_template(appliance, provider, template, service_catalogs,
                                            request):
    """
    Steps:
    1. Order Service which uses Orchestration template
    2. Try to remove this Orchestration template

    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: stack
    """
    provision_request = service_catalogs.order()
    request.addfinalizer(lambda: prov_req_cleanup(appliance, provision_request))
    template.delete()
    wait_for(lambda: provision_request.status == 'Error', timeout='5m')
    assert not template.exists


@pytest.mark.meta(blockers=[BZ(1754543)])
@pytest.mark.provider([OpenStackProvider, AzureProvider, EC2Provider],
                      selector=ONE_PER_TYPE, scope='module')
def test_remove_read_only_orch_template_neg(appliance, provider, template, order_stack, request):
    """
    For RHOS/Azure the original template will remain stand-alone while the stack links
    to a new template read from the RHOS/Azure provider. Hence we can delete used orchestration
    template for RHOS/Azure.

    Steps:
    1. Order Service which uses Orchestration template
    2. Try to remove this Orchestration template
    3. Check if remove item is disabled.

    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: stack
    """
    view = navigate_to(template, 'Details')
    msg = "Remove this Orchestration Template from Inventory"
    wait_for(func=view.toolbar.configuration.item_enabled,
             func_args=(msg,),
             fail_condition=True,
             fail_func=view.browser.refresh,
             timeout='1m')
    if provider.one_of(OpenStackProvider, AzureProvider):
        wait_for(func=view.toolbar.configuration.item_enabled,
                func_args=(msg,),
                fail_condition=False,
                fail_func=view.browser.refresh,
                timeout='3m')
    # We expect the stack to get created fine, so let's check that.
    order_stack.wait_for_request()
    assert order_stack.is_succeeded()


def test_retire_stack(stack_created):
    """Tests stack retirement.

    Steps:
    1. Retire Orchestration stack
    2. Verify it doesn't exist in UI

    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: stack
    """
    stack_created.retire_stack()
    assert not stack_created.exists, "Stack still visible in UI"


@test_requirements.service
@test_requirements.azure
@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1410794])
@pytest.mark.provider([AzureProvider], selector=ONE, scope='module')
def test_error_message_azure(order_stack):
    """
    Starting with 5.8, error messages generated by azure when provisioning
    from orchestration template will be included in the Last Message
    field.  Users will no longer have to drill down to Stack/Resources to
    figure out the error.
    This is currently working correctly as of 5.8.0.12

    Bugzilla:
        1410794

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/4h
        setup: Easiest way to do this is provision an azure vm from orchestration
               catalog item and just add a short password like "test".  This will
               fail on the azure side and the error will be displayed in the request
               details.
        startsin: 5.8
    """
    msg = "Orchestration stack deployment error: The supplied password must be"
    with LogValidator('/var/www/miq/vmdb/log/evm.log',
                      matched_patterns=[msg],
                      ).waiting(timeout=450):
        provision_request = order_stack
        provision_request.wait_for_request(method='ui')
        assert not provision_request.is_succeeded()


@pytest.mark.manual
@test_requirements.azure
@pytest.mark.tier(2)
def test_stack_template_azure():
    """
    There was a new field added to Orchestration stacks to show which
    image was used to create it.  You need to verify the end points of
    this image are displayed correctly.
    This just needs to be checked every once in a while.  Perhaps once per
    build.  Should be able to automate it by comparing the yaml entries to
    the value.

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: low
        initialEstimate: 1/8h
        setup: Create a stack based on a cloud image.  Go to stack details and check
               the
        upstream: yes
    """
    pass


@pytest.mark.meta(blockers=[BZ(1754543, forced_streams=["5.11"])], automates=[1684092])
@pytest.mark.customer_scenario
@pytest.mark.tier(2)
@pytest.mark.provider([EC2Provider], selector=ONE, scope='module')
def test_retire_catalog_bundle_service_orchestration_item(appliance, request, catalog_item,
                                                          stack_data):
    """
    Bugzilla:
        1684092
    Polarion:
        assignee: nansari
        startsin: 5.10
        casecomponent: Services
        initialEstimate: 1/6h
        testSteps:
            1. Add ec2 provider
            2. Provisioned the catalog bundle with ServiceOrchestration item
            3. Navigate to My service page
            4. Retired the bundle
        expectedResults:
            1.
            2.
            3.
            4. Catalog bundle should retire with no error
    """
    bundle_name = fauxfactory.gen_alphanumeric(15, start="cat_bundle_")
    catalog_bundle = appliance.collections.catalog_bundles.create(
        bundle_name, description="catalog_bundle",
        display_in=True, catalog=catalog_item.catalog,
        dialog=catalog_item.dialog,
        catalog_items=[catalog_item.name])
    request.addfinalizer(catalog_bundle.delete_if_exists)

    # Ordering service catalog bundle
    service_catalogs = ServiceCatalogs(
        appliance, catalog_bundle.catalog, catalog_bundle.name, stack_data)

    provision_request = service_catalogs.order()
    provision_request.wait_for_request(method='ui')
    provision_request.is_succeeded(method="ui")

    last_message = provision_request.get_request_row_from_ui()['Last Message'].text
    service_name = last_message.split()[2].strip('[]')
    service = MyService(appliance, service_name)

    @request.addfinalizer
    def _clear_request_service():
        if provision_request.exists():
            provision_request.remove_request(method="rest")
        if service.exists:
            service.delete()

    assert service.exists

    # Retire service
    retire_request = service.retire()

    @request.addfinalizer
    def _clear_retire_request():
        if retire_request.exists():
            retire_request.remove_request()

    wait_for(
        lambda: service.is_retired,
        delay=5, num_sec=120,
        fail_func=service.browser.refresh,
        message="waiting for service retire"
    )


@pytest.mark.meta(automates=[1698439])
@pytest.mark.tier(2)
@pytest.mark.provider([EC2Provider], selector=ONE, scope='module')
def test_read_dialog_timeout_ec2_stack(order_stack):
    """
    Bugzilla:
        1698439
    Polarion:
        assignee: nansari
        startsin: 5.10
        casecomponent: Services
        initialEstimate: 1/6h
        testSteps:
            1. create an aws template with an optional value "timeout"
            2. create a dialog that will offer an option to overwrite "timeout"
               with a custom value typed at input
            3. Navigate to order page of service
            4. provision using a non-zero value in timeout
        expectedResults:
            1.
            2.
            3.
            4. the value input should be passed
    """
    msg = "<AEMethod groupsequencecheck>.*dialog_stack_timeout: 20"
    with LogValidator('/var/www/miq/vmdb/log/evm.log',
                      matched_patterns=[msg],
                      ).waiting(timeout=450):
        provision_request = order_stack
        provision_request.wait_for_request(method='ui')
        provision_request.is_succeeded()
