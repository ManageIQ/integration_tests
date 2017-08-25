# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.infrastructure.provider import InfraProvider
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.automate.explorer.domain import DomainCollection
from cfme.services import requests
from cfme import test_requirements
from utils.log import logger
from utils.update import update
from utils import testgen


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('vm_name', 'catalog_item', 'uses_infra_providers'),
    test_requirements.service,
    pytest.mark.long_running
]


pytest_generate_tests = testgen.generate([InfraProvider], required_fields=[
    ['provisioning', 'template'],
    ['provisioning', 'host'],
    ['provisioning', 'datastore']
], scope="module")


@pytest.fixture(scope="function")
def create_domain(request):
    """Create new domain and copy instance from ManageIQ to this domain"""

    dc = DomainCollection()
    new_domain = dc.create(name=fauxfactory.gen_alphanumeric(), enabled=True)
    request.addfinalizer(new_domain.delete_if_exists)
    instance = dc.instantiate(name='ManageIQ')\
        .namespaces.instantiate(name='Service')\
        .namespaces.instantiate(name='Provisioning')\
        .namespaces.instantiate(name='StateMachines')\
        .classes.instantiate(name='ServiceProvisionRequestApproval')\
        .instances.instantiate(name='Default')
    instance.copy_to(new_domain)
    return new_domain


@pytest.fixture(scope="function")
def modify_instance(create_domain):
    """Modify the instance in new domain to change it to manual approval instead of auto"""

    instance = create_domain.namespaces.instantiate(name='Service')\
        .namespaces.instantiate(name='Provisioning')\
        .namespaces.instantiate(name='StateMachines')\
        .classes.instantiate(name='ServiceProvisionRequestApproval')\
        .instances.instantiate(name='Default')
    with update(instance):
        instance.fields = {"approval_type ": {"value": "manual"}}


@pytest.mark.ignore_stream("upstream")
@pytest.mark.tier(2)
def test_service_manual_approval(provider, setup_provider, modify_instance, catalog_item, request):
    """Tests order catalog item
    Metadata:
        test_flag: provision
    """
    vm_name = catalog_item.provisioning_data["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    catalog_item.create()

    service_catalogs = ServiceCatalogs(catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info("Waiting for cfme provision request for service {}".format(catalog_item.name))
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row = requests.find_request(cells, True)
    assert row.approval_state.text == 'Pending Approval'
