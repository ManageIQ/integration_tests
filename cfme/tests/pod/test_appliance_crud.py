import pytest


@pytest.mark.manual
def test_crud_pod_appliance():
    """
    deploys pod appliance
    checks that it is alive
    deletes pod appliance
    """
    pass


@pytest.mark.manual
def test_crud_pod_appliance_ansible_deployment():
    """
    deploys pod appliance
    checks that it is alive
    deletes pod appliance
    """
    pass


@pytest.mark.manual
def test_crud_pod_appliance_ext_db():
    """
    deploys pod appliance
    checks that it is alive
    deletes pod appliance
    """
    pass


@pytest.mark.manual
def test_crud_pod_appliance_custom_config():
    """
    overriding default values in template and deploys pod appliance
    checks that it is alive
    deletes pod appliance
    """
    pass


@pytest.mark.manual
def test_pod_appliance_config_upgrade():
    """
    appliance config update should cause appliance re-deployment
    """
    pass


@pytest.mark.manual
def test_pod_appliance_image_upgrade():
    """
    one of appliance images has been changed. it should cause pod re-deployment
    """
    pass


@pytest.mark.manual
def test_pod_appliance_db_upgrade():
    """
    db scheme/version has been changed
    """
    pass


@pytest.mark.manual
def test_pod_appliance_start_stop():
    """
    appliance should start w/o issues
    """
    pass


@pytest.mark.manual
def test_pod_appliance_scale():
    """
    appliance should work correctly after scale up/down
    """
    pass


@pytest.mark.manual
def test_aws_smartstate_pod():
    """
    deploy aws smartstate pod and that it works
    """
    pass
