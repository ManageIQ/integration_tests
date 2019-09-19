# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.config_management.ansible_tower import AnsibleTowerProvider
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log_validator import LogValidator

pytestmark = [
    test_requirements.automate,
    pytest.mark.provider([AnsibleTowerProvider], scope='module'),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture(scope="function")
def ansible_catalog_item(appliance, request, provider, ansible_tower_dialog, catalog):
    config_manager_obj = provider
    provider_name = config_manager_obj.data.get('name')
    template = config_manager_obj.data['provisioning_data']['template']
    cat_list = []
    for _ in range(2):
        catalog_item = appliance.collections.catalog_items.create(
            appliance.collections.catalog_items.ANSIBLE_TOWER,
            name=ansible_tower_dialog.label,
            description=fauxfactory.gen_alphanumeric(),
            display_in=True,
            catalog=catalog,
            dialog=ansible_tower_dialog,
            provider=f'{provider_name} Automation Manager',
            config_template=template)
        cat_list.append(catalog_item.name)
        request.addfinalizer(catalog_item.delete_if_exists)
    return cat_list


@pytest.fixture
def set_roottenant_quota(request, appliance):
    roottenant = appliance.collections.tenants.get_root_tenant()
    field, value = request.param
    roottenant.set_quota(**{f'{field}_cb': True, field: value})
    yield
    roottenant.set_quota(**{f'{field}_cb': False})


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1363901])
@pytest.mark.parametrize(
    ("set_roottenant_quota"),
    [("storage", 1)],
    indirect=["set_roottenant_quota"],
    ids=["max_storage"],
)
def test_quota_for_ansible_service(request, appliance, ansible_catalog_item, catalog,
                                   ansible_tower_dialog, set_roottenant_quota):
    """
    Bugzilla:
        1363901

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        caseimportance: low
        caseposneg: positive
        testtype: functional
        startsin: 5.5
        casecomponent: Configuration
        testSteps:
            1. create a service bundle including an Ansible Tower service type
            2. make sure CloudForms quotas are enabled
            3. provision the service
        expectedResults:
            1.
            2.
            3. No error in service bundle provisioning for Ansible Tower service types when quota
               is enforce.
    """
    bundle_name = fauxfactory.gen_alphanumeric(start="bundle_")
    catalog_bundle = appliance.collections.catalog_bundles.create(
        bundle_name,
        description="catalog_bundle",
        display_in=True,
        catalog=catalog,
        dialog=ansible_tower_dialog,
        catalog_items=ansible_catalog_item,
    )
    request.addfinalizer(catalog_bundle.delete_if_exists)
    service_catalogs = ServiceCatalogs(appliance, catalog_bundle.catalog, catalog_bundle.name)

    with LogValidator(
            "/var/www/miq/vmdb/log/automation.log", failure_patterns=[".*ERROR.*"]
    ).waiting(timeout=120):
        service_catalogs.order()
        provision_request = appliance.collections.requests.instantiate(
            bundle_name, partial_check=True
        )

        @request.addfinalizer
        def delete():
            # Need to navigate on other page. So that, delete button will appear on requests details
            # page.
            navigate_to(appliance.server, "Dashboard")
            provision_request.remove_request()

        provision_request.wait_for_request()
        msg = "Provisioning failed with the message {}".format(provision_request.rest.message)
        assert provision_request.is_succeeded(), msg
