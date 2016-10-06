# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from cfme.services.catalogs.myservice import MyService
from cfme.automate.simulation import simulate
from cfme.automate.explorer import Domain, Namespace, Class, Method
from cfme import test_requirements
from utils import testgen
from utils.log import logger
from utils.wait import wait_for


pytestmark = [
    test_requirements.service,
    pytest.mark.usefixtures("vm_name"),
    pytest.mark.usefixtures("catalog_item"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.long_running,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.tier(3)
]


pytest_generate_tests = testgen.generate(testgen.provider_by_type, ['virtualcenter'],
    scope="module")


@pytest.fixture(scope="function")
def copy_domain(request):
    domain = Domain(name=fauxfactory.gen_alphanumeric(), enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture
def myservice(setup_provider, provider, catalog_item, request):
    vm_name = catalog_item.provisioning_data["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog.name, catalog_item)
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=900, delay=20)
    assert row.request_state.text == 'Finished'
    return MyService(catalog_item.name, vm_name)


def test_add_vm_to_service(myservice, request, copy_domain):
    """Tests adding vm to service

    Metadata:
        test_flag: provision
    """
    method_torso = """
    def add_to_service
        vm      = $evm.root['vm']
        service = $evm.vmdb('service').find_by_name('{}')
        user    = $evm.root['user']

    if service && vm
        $evm.log('info', "XXXXXXXX Attaching Service to VM: [#{{service.name}}][#{{vm.name}}]")
        vm.add_to_service(service)
        vm.owner = user if user
        vm.group = user.miq_group if user
    end
    end

    $evm.log("info", "Listing Root Object Attributes:")
    $evm.log("info", "===========================================")

    add_to_service
    """.format(myservice.service_name)

    method = Method(
        name="InspectMe",
        data=method_torso,
        cls=Class(
            name="Request",
            namespace=Namespace(
                name="System",
                parent=copy_domain
            )
        )
    )
    method.create()
    request.addfinalizer(lambda: method.delete() if method.exists() else None)
    simulate(
        instance="Request",
        message="create",
        request=method.name,
        attribute=["VM and Instance", "auto_test_services"],  # Random selection, does not matter
        execute_methods=True
    )
    myservice.check_vm_add("auto_test_services")
    request.addfinalizer(lambda: myservice.delete(myservice.service_name))
