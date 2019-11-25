import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.requests import RequestDetailsToolBar
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.update import update


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('setup_provider_modscope', 'catalog_item', 'uses_infra_providers'),
    test_requirements.service,
    pytest.mark.long_running,
    pytest.mark.provider([InfraProvider], selector=ONE_PER_TYPE,
                         required_fields=[['provisioning', 'template'],
                                          ['provisioning', 'host'],
                                          ['provisioning', 'datastore']],
                         scope="module"),
]


@pytest.fixture(scope='function')
def service_retirement_request(domain):
    domain.parent.instantiate(name="ManageIQ").namespaces.instantiate(
        name="Service").namespaces.instantiate(
        name="Retirement").namespaces.instantiate(
        name="StateMachines").classes.instantiate(
        name="ServiceRetirementRequestApproval").instances.instantiate(
        name="Default").copy_to(domain.name)

    method = domain.namespaces.instantiate(
        name="Service").namespaces.instantiate(
        name="Retirement").namespaces.instantiate(
        name="StateMachines").classes.instantiate(
        name="ServiceRetirementRequestApproval").instances.instantiate(
        name="Default")

    with update(method):
        method.fields = {"approval_type": {"value": "manual"}}

    return method


@pytest.fixture(scope="function")
def create_domain(request, appliance):
    """Create new domain and copy instance from ManageIQ to this domain"""

    dc = DomainCollection(appliance)
    new_domain = dc.create(name=fauxfactory.gen_alphanumeric(12, start="domain_"), enabled=True)
    request.addfinalizer(new_domain.delete_if_exists)
    instance = (dc.instantiate(name='ManageIQ')
        .namespaces.instantiate(name='Service')
        .namespaces.instantiate(name='Provisioning')
        .namespaces.instantiate(name='StateMachines')
        .classes.instantiate(name='ServiceProvisionRequestApproval')
        .instances.instantiate(name='Default'))
    instance.copy_to(new_domain)
    return new_domain


@pytest.fixture(scope="function")
def modify_instance(create_domain):
    """Modify the instance in new domain to change it to manual approval instead of auto"""

    instance = (create_domain.namespaces.instantiate(name='Service')
        .namespaces.instantiate(name='Provisioning')
        .namespaces.instantiate(name='StateMachines')
        .classes.instantiate(name='ServiceProvisionRequestApproval')
        .instances.instantiate(name='Default'))
    with update(instance):
        instance.fields = {"approval_type": {"value": "manual"}}


@pytest.mark.rhv3
@pytest.mark.meta(blockers=[BZ(1633540, forced_streams=['5.10'],
    unblock=lambda provider: not provider.one_of(RHEVMProvider))])
@pytest.mark.ignore_stream("upstream")
@pytest.mark.tier(2)
def test_service_manual_approval(appliance, provider, modify_instance,
                                 catalog_item, request):
    """Tests order catalog item
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: service
    """
    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(vm_name,
                                                            provider).cleanup_on_provider()
    )

    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info("Waiting for cfme provision request for service {}".format(catalog_item.name))
    request_description = catalog_item.name
    service_request = appliance.collections.requests.instantiate(description=request_description,
                                                                 partial_check=True)
    service_request.update(method='ui')
    assert service_request.row.approval_state.text == 'Pending Approval'


@pytest.mark.meta(automates=[BZ(1697600)])
@pytest.mark.provider([VMwareProvider], scope="module")
@pytest.mark.customer_scenario
def test_service_retire_manual_approval(request, appliance, service_retirement_request, service_vm):
    """ Test service retirement manual approval

    Bugzilla:
        1697600

    Polarion:
        assignee: nansari
        initialEstimate: 1/2h
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Services
        setup:
            1. Set Service retirement manual approval instead of auto
        testSteps:
            1. Add Service Catalog, Order the Service
            2. Retire the service
            3. Navigate to Service retirement request Details page
            4. Manually approve the service retirement request
        expectedResults:
            1.
            2.
            3.
            4. Admin should be able to approve the retirement request
    """
    service, _ = service_vm
    with appliance.context.use(ViaUI):
        service.retire(wait=False)
        request_description = f"Service Retire for: {service.name}"
        service_request = appliance.collections.requests.instantiate(
            description=request_description,
            partial_check=True)
        service_request.update(method='ui')
        assert service_request.row.approval_state.text == 'Pending Approval'
        # TODO(BZ-1721479): Remove the work-around once this BZ got fixed
        navigate_to(service_request, "Details")
        view = appliance.browser.create_view(RequestDetailsToolBar)
        if not view.approve.is_displayed and BZ(1721479, forced_streams=['5.10', '5.11']).blocks:
            navigate_to(appliance.server, "Dashboard")
            service_request.approve_request(method='ui', reason="Approved")
        else:
            service_request.approve_request(method='ui', reason="Approved")
        assert service_request.row.approval_state.text == 'Approved'
        service_request.wait_for_request()
        msg = "Request failed with the message {}".format(service_request.rest.message)
        request.addfinalizer(service_request.remove_request)
        assert service_request.is_succeeded(), msg
