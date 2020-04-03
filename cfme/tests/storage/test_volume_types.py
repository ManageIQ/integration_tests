import pytest


def test_storage_volume_type_present():
    view = navigate_to(ec2_provider, 'Details')
    block_storage_manager_relationship_fields = view.entities.relationships.fields
    if 'Cloud Volume Types' not in block_storage_manager_relationship_fields:
        pytest.fail()