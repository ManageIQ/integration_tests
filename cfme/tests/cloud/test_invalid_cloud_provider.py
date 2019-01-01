import pytest
from cfme.base.utils import BZ

def test_openstack_provider_invalid_details():
    """
        This test case checks openstack provider addition with various incorrect provider details.
            -test Name
            -test incorrect format of Name
            (all combinations of following)
            -test Hostname
            -test incorrect format of Hostname
            -test incorrect Hostname
            -test Security Protocol
            -test incorrect Security Protocol
            -test Username
            -test incorrect format of Username
            -test incorrect Username
            -test Password
            -test incorrect format of Password
            -test incorrect Password
            -test Validate
            -test switching Security Protocol
            Events > AMQP
            (all combinations of following)
            -test Hostname
            -test incorrect format of Hostname
            -test incorrect Hostname
            -test API Port
            -test incorrect format of API Port
            -test incorrect API Port
            -test Security Protocol
            -test incorrect Security Protocol
            -test Username
            -test incorrect format of Username
            -test incorrect Username
            -test Password
            -test incorrect format of Password
            -test incorrect Password
            -test Validate
            -test switching Security Protocol

    """
    pass


def test_azure_provider_invalid_details():
    """
    This test case checks azure provider addition with various incorrect provider details.
        -test Name
        -test incorrect format of Name
        (all combinations of following)
        -test Region
        -test incorrect Region
        -test Tenant ID
        -test incorrect format of Tenant ID
        -test incorrect Tenant ID
        -test Subscription ID
        -test incorrect format of Subscription ID
        -test incorrect Subscription ID
        (all combinations of following)
        -test Client ID
        -test incorrect format of Client ID
        -test incorrect Client ID
        -test Client Key
        -test incorrect format of Client Key
        -test incorrect Client Key
        -test Confirm Client Key
        -test incorrect format of Confirm Client Key
        -test incorrect Confirm Client Key
        -test Validate

    """
    pass


@pytest.mark.uncollectif(lambda appliance: appliance.version >= "5.10")
def test_gce_provider_invalid_details(appliance):
    """
    This test case checks gce provider addition with various incorrect provider details.
        -test Name
        -test incorrect format of Name
        (all combinations of following)
        -test Region
        -test incorrect Region
        -test Project
        -test incorrect format of Project
        -test incorrect Project
        -test Service Account JSON
        -test incorrect format of Service Account JSON
        -test incorrect Service Account JSON
        -test Validate

    """
    pass


def test_amazon_provider_invalid_details(appliance):
    """
    This test case checks amazon ec2 provider addition with various incorrect provider details.
        -test Name
        -test incorrect format of Name
        (all combinations of following)
        -test Region
        -test incorrect Region
        -test Access Key ID
        -test incorrect format of Access Key ID
        -test incorrect Access Key ID
        -test Secret Access Key
        -test incorrect format of Secret Access Key
        -test incorrect Secret Access Key
        -test Confirm Secret Access Key
        -test incorrect format of Confirm Secret Access Key
        -test incorrect Confirm Secret Access Key
        -test Validate
    """
    pass
