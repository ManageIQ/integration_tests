"""Test to validate End-to-End migrations- functional testing."""
import pytest

from cfme.fixtures.provider import rhel7_minimal
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION, ONE_PER_TYPE

pytestmark = [
    pytest.mark.provider(
        classes=[RHEVMProvider], selector=ONE_PER_VERSION, required_flags=["v2v"], scope="module"
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        fixture_name="source_provider",
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.usefixtures("v2v_providers", "host_creds", "conversion_tags"),
]


@pytest.mark.parametrize(
    "form_data_vm_obj_single_datastore", [["nfs", "nfs", rhel7_minimal]], indirect=True
)
def test_infrastructure_maping_crud(request, appliance, form_data_vm_obj_single_datastore):
    """ Test create and delete for Infra Mapping
    Polarion:
        assignee: sshveta
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
        testSteps:
            1. V2V providers have to be added to create Mapping
            2. Authenticate Host and conversion tags
            3. create mapping with nfs source and nfs target datastore
    """

    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore.form_data)
    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)


