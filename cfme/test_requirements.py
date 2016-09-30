"""Test requirements mapping

This module contains predefined pytest markers for CFME product requirements.

Please import the module instead of elements:

.. code-block:: python

    from cfme import test_requirements

    pytestmark = [test_requirements.alert]

    @test_requirments.quota
    def test_quota_alert():
        pass

"""

import pytest

alert = pytest.mark.requirement("alert")
auth = pytest.mark.requirement("auth")
automate = pytest.mark.requirement("automate")
black = pytest.mark.requirement("black")
c_and_u = pytest.mark.requirement("c_and_u")
chargeback = pytest.mark.requirement("chargeback")
run_process = pytest.mark.requirement("run_process")
control = pytest.mark.requirement("control")
cloud_init = pytest.mark.requirement("cloud_init")
dashboard = pytest.mark.requirement("dashboard")
distributed = pytest.mark.requirement("distributed")
drift = pytest.mark.requirement("drift")
timelines = pytest.mark.requirement("timelines")
general_ui = pytest.mark.requirement("general_ui")
html5 = pytest.mark.requirement("html5")
ipv6 = pytest.mark.requirement("ipv6")
log_depot = pytest.mark.requirement("log_depot")
cfme_tenancy = pytest.mark.requirement("cfme_tenancy")
right_size = pytest.mark.requirement("right_size")
upgrade = pytest.mark.requirement("upgrade")
provision = pytest.mark.requirement("provision")
bottleneck = pytest.mark.requirement("bottleneck")
ownership = pytest.mark.requirement("ownership")
quota = pytest.mark.requirement("quota")
rbac = pytest.mark.requirement("rbac")
access = pytest.mark.requirement("access")
report = pytest.mark.requirement("report")
rest = pytest.mark.requirement("rest")
rep = pytest.mark.requirement("rep")
power = pytest.mark.requirement("power")
discovery = pytest.mark.requirement("discovery")
filter = pytest.mark.requirement("filter")
ssui = pytest.mark.requirement("ssui")
stack = pytest.mark.requirement("stack")
smartstate = pytest.mark.requirement("smartstate")
snapshot = pytest.mark.requirement("snapshot")
sdn = pytest.mark.requirement("sdn")
sysprep = pytest.mark.requirement("sysprep")
tag = pytest.mark.requirement("tag")
genealogy = pytest.mark.requirement("genealogy")
retirement = pytest.mark.requirement("retirement")
vm_migrate = pytest.mark.requirement("vm_migrate")
reconfigure = pytest.mark.requirement("reconfigure")
vmrc = pytest.mark.requirement("vmrc")
configuration = pytest.mark.requirement("configuration")
