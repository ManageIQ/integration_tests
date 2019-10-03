import fauxfactory
import pytest
from wait_for import wait_for

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import providers
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.datafile import load_data_file
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
def stack_data(appliance, provider, provisioning):
    random_base = fauxfactory.gen_alphanumeric()
    stackname = 'test{}'.format(random_base)
    vm_name = 'test-{}'.format(random_base)
    stack_timeout = '20'
    if provider.one_of(AzureProvider):
        try:
            template = provider.data.templates.small_template
            vm_user = credentials[template.creds].username
            vm_password = credentials[template.creds].password
        except AttributeError:
            pytest.skip('Could not find small_template or credentials for {}'.format(provider.name))

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
    return 'dialog_{}'.format(fauxfactory.gen_alphanumeric())


@pytest.fixture
def template(appliance, provider, provisioning, dialog_name):
    template_group = provisioning['stack_provisioning']['template_type']
    template_type = provisioning['stack_provisioning']['template_type_dd']
    template_name = fauxfactory.gen_alphanumeric()
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
    cat_name = "cat_{}".format(fauxfactory.gen_alphanumeric())
    catalog = appliance.collections.catalogs.create(name=cat_name, description="my catalog")
    yield catalog
    if catalog.exists:
        catalog.delete()


@pytest.fixture
def catalog_item(appliance, dialog, catalog, template, provider, dialog_name):
    item_name = fauxfactory.gen_alphanumeric()
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
def stack(appliance, provider, stack_data):
    return appliance.collections.cloud_stacks.instantiate(stack_data['stack_name'],
                                                          provider=provider)


@pytest.fixture
def order_stack(appliance, service_catalogs, stack):
    """Fixture which prepares provisioned stack"""
    provision_request = service_catalogs.order()
    provision_request.wait_for_request(method='ui')
    assert provision_request.is_succeeded()
    stack.wait_for_exists()
    yield provision_request, stack
    _cleanup(appliance, provision_request)
    stack.wait_for_not_exists()


def _cleanup(appliance=None, provision_request=None, service=None):
    if not service:
        last_message = provision_request.get_request_row_from_ui()['Last Message'].text
        service_name = last_message.split()[2].strip('[]')
        myservice = MyService(appliance, service_name)
    else:
        myservice = service
    if myservice.exists:
        myservice.retire()
        myservice.delete()


@pytest.mark.meta(blockers=[BZ(1754543)])
def test_provision_stack(order_stack):
    """Tests stack provisioning

    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
        initialEstimate: 1/3h
        casecomponent: Provisioning
    """
    provision_request, stack = order_stack
    assert provision_request.is_succeeded()
    assert stack.exists


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
    request.addfinalizer(lambda: _cleanup(service=myservice))
    assert provision_request.is_succeeded()
    myservice.reconfigure_service()


# EC2 locks template between Stack order and template removal'
@pytest.mark.provider(gen_func=providers,
                      filters=[cloud_filter, not_ec2],
                      override=True,
                      selector=ONE_PER_TYPE,
                      scope='module')
@pytest.mark.meta(blockers=[BZ(1754543)])
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
    request.addfinalizer(lambda: _cleanup(appliance, provision_request))
    template.delete()
    wait_for(lambda: provision_request.status == 'Error', timeout='5m')
    assert not template.exists


@pytest.mark.meta(blockers=[BZ(1754543)])
@pytest.mark.provider([EC2Provider], selector=ONE_PER_TYPE, override=True, scope='module')
def test_remove_read_only_orch_template_neg(appliance, provider, template, service_catalogs,
                                            request):
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
    provision_request = service_catalogs.order()
    request.addfinalizer(lambda: _cleanup(appliance, provision_request))
    provision_request.wait_for_request(method='ui')
    view = navigate_to(template, 'Details')
    msg = "Remove this Orchestration Template from Inventory"
    assert not view.toolbar.configuration.item_enabled(msg)


@pytest.mark.meta(blockers=[BZ(1754543)])
def test_retire_stack(order_stack):
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
    _, stack = order_stack
    stack.retire_stack()
    assert not stack.exists, "Stack still visible in UI"


@pytest.mark.manual
@test_requirements.service
@test_requirements.azure
@pytest.mark.tier(1)
def test_error_message_azure():
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
    pass


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
