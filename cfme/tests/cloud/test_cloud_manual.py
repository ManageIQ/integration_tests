# -*- coding: utf-8 -*-
"""Manual tests"""

import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.ignore_stream("5.9", "5.10", "upstream")]


@pytest.mark.manual
@pytest.mark.tier(1)
@test_requirements.discovery
def test_add_cloud_provider_screen():
    """
    Polarion:
        assignee: pvala
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 3h
        testSteps:
            Add cloud provider using Add Provider screen:
            1.Open Stack:
                -test Name
                -test incorrect format of Name
                (all combinations of following)
                -test Hostname
                -test incorrect format of Hostname
                -test incorrect Hostname
                -test Security Protocol
                -test incorrect Security Protocol
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
            2. Amazon EC2:
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
            3. Azure:
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
                -test Validate
            4. Google Compute Engine
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
