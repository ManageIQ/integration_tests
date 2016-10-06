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

access = pytest.mark.requirement("access")
alert = pytest.mark.requirement("alert")
auth = pytest.mark.requirement("auth")
automate = pytest.mark.requirement("automate")
black = pytest.mark.requirement("black")
bottleneck = pytest.mark.requirement("bottleneck")
c_and_u = pytest.mark.requirement("c_and_u")
cfme_tenancy = pytest.mark.requirement("cfme_tenancy")
chargeback = pytest.mark.requirement("chargeback")
cloud_init = pytest.mark.requirement("cloud_init")
config_management = pytest.mark.requirement("config_management")
configuration = pytest.mark.requirement("configuration")
control = pytest.mark.requirement("control")
dashboard = pytest.mark.requirement("dashboard")
discovery = pytest.mark.requirement("discovery")
distributed = pytest.mark.requirement("distributed")
drift = pytest.mark.requirement("drift")
filter = pytest.mark.requirement("filter")
genealogy = pytest.mark.requirement("genealogy")
general_ui = pytest.mark.requirement("general_ui")
html5 = pytest.mark.requirement("html5")
ipv6 = pytest.mark.requirement("ipv6")
log_depot = pytest.mark.requirement("log_depot")
ownership = pytest.mark.requirement("ownership")
power = pytest.mark.requirement("power")
provider_discovery = pytest.mark.requirement("provider_discovery")
provision = pytest.mark.requirement("provision")
quota = pytest.mark.requirement("quota")
rbac = pytest.mark.requirement("rbac")
reconfigure = pytest.mark.requirement("reconfigure")
rep = pytest.mark.requirement("rep")
report = pytest.mark.requirement("report")
rest = pytest.mark.requirement("rest")
retirement = pytest.mark.requirement("retirement")
right_size = pytest.mark.requirement("right_size")
run_process = pytest.mark.requirement("run_process")
sdn = pytest.mark.requirement("sdn")
service = pytest.mark.requirement("service")
settings = pytest.mark.requirement("settings")
smartstate = pytest.mark.requirement("smartstate")
snapshot = pytest.mark.requirement("snapshot")
ssui = pytest.mark.requirement("ssui")
stack = pytest.mark.requirement("stack")
sysprep = pytest.mark.requirement("sysprep")
tag = pytest.mark.requirement("tag")
timelines = pytest.mark.requirement("timelines")
upgrade = pytest.mark.requirement("upgrade")
vm_migrate = pytest.mark.requirement("vm_migrate")
vmrc = pytest.mark.requirement("vmrc")
