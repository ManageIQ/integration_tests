# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from wait_for import wait_for

from cfme import test_requirements
from cfme.fixtures.automate import DatastoreImport
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('setup_provider', 'uses_infra_providers'),
    test_requirements.customer_stories,
    test_requirements.service,
    pytest.mark.long_running,
    pytest.mark.provider([InfraProvider], selector=ONE_PER_TYPE,
                         required_fields=[['provisioning', 'template'],
                                          ['provisioning', 'host'],
                                          ['provisioning', 'datastore']],
                         scope="module"),
]


@pytest.mark.rhv3
@pytest.mark.tier(2)
def test_edit_bundle_entry_point(appliance, provider, catalog_item, request):
    """Tests editing a catalog bundle enrty point and check if the value is saved.
    Metadata:
        test_flag: provision

    Bugzilla:
        1698431

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """
    prov_entry_point = (
        "Datastore",
        "ManageIQ (Locked)",
        "Service",
        "Provisioning",
        "StateMachines",
        "ServiceProvision_Template",
        "CatalogItemInitialization"
    )

    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            "{}0001".format(vm_name), provider).cleanup_on_provider()
    )
    bundle_name = fauxfactory.gen_alphanumeric()
    catalog_bundle = appliance.collections.catalog_bundles.create(
        bundle_name,
        catalog_items=[catalog_item.name],
        catalog=catalog_item.catalog,
        description="catalog_bundle",
        display_in=True,
        dialog=catalog_item.dialog,
        provisioning_entry_point=prov_entry_point
    )
    view = navigate_to(catalog_bundle, "Edit")
    assert view.basic_info.provisioning_entry_point.value == ("/Service/Provisioning/StateMachines/"
                                                              "ServiceProvision_Template/"
                                                              "CatalogItemInitialization")
    view.cancel_button.click()


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[BZ(1705021)])
@pytest.mark.customer_scenario
@pytest.mark.parametrize(
    "import_data",
    [DatastoreImport("bz_1705021.zip", "bz_1705021", None)],
    ids=["sample_domain"],
)
# Parametrizing for import_dialog fixture
@pytest.mark.parametrize("file_name", ["bz_1705021.yml"],
    ids=["sample_dialog"],
)
def test_refresh_dynamic_field(appliance, import_datastore, import_data,
                               catalog_item_with_imported_dialog):
    """Tests refresh dynamic field when field name has 'password' in label.
    Metadata:
        test_flag: provision

    Bugzilla:
        1705021

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    setup:
        1. Import bz dialog
        2. Import  bz datastore
        3. Create catalog item
    testSteps:
        1. Order service catalog and refresh dynamic field
    expectedResults:
        1. Refreshing dynamic field should work and submit button should enable
    """
    cat_item, ele_label = catalog_item_with_imported_dialog
    service_catalogs = ServiceCatalogs(appliance, cat_item.catalog, cat_item.name)
    view = navigate_to(service_catalogs, 'Order')
    view.wait_displayed("5s")
    view.fields(ele_label).fill("Password")
    # If Refresh works submit button will enable
    wait_for(lambda: not view.submit_button.disabled, timeout=7)
