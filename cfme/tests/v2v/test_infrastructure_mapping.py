"""Test to validate End-to-End migrations- functional testing."""
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.provider import rhel7_minimal
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION

pytestmark = [
    test_requirements.v2v,
    pytest.mark.provider(
        classes=[OpenStackProvider, RHEVMProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"],
        scope="module"
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        fixture_name="source_provider",
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.usefixtures("v2v_provider_setup"),
]


@pytest.mark.parametrize(
    "mapping_data_vm_obj_single_datastore", [["nfs", "nfs", rhel7_minimal]], indirect=True
)
def test_infrastructure_mapping_crud(request, appliance, mapping_data_vm_obj_single_datastore):
    """ Test create and delete for Infra Mapping
    Polarion:
        assignee: sshveta
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        customerscenario: true
        initialEstimate: 1/4h
        testSteps:
            1. V2V providers have to be added to create Mapping (Vmware and RHV/OSP)
            2. create mapping with nfs source and nfs target datastore
    """

    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping_data = mapping_data_vm_obj_single_datastore.infra_mapping_data

    mapping = infrastructure_mapping_collection.create(**mapping_data)
    assert infrastructure_mapping_collection.mapping_exists(mapping.name)
    if appliance.version >= "5.10":
        mapping = mapping.update(mapping_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
