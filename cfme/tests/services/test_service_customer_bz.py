# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('setup_provider', 'catalog_item', 'uses_infra_providers'),
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
