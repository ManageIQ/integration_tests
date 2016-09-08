import pytest
from utils import testgen
from cfme.web_ui import Quadicon, toolbar
from cfme.infrastructure.host import Host
from cfme.web_ui import InfoBlock
from cfme.fixtures import pytest_selenium as sel
from cfme.configure.tasks import is_host_analysis_finished
from utils.wait import wait_for


pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'],
                                         scope='module')


NODE_TYPE = "Compute"

"""
    currently take nova compute node with an instance configured and nova
    as availability zone
"""


@pytest.mark.usefixtures("setup_provider_modscope")
def test_host_assigned_zones(provider):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        if quad.name != NODE_TYPE:
            break
        host = Host(name=quad.name)
        host.run_smartstate_analysis()
        wait_for(lambda: is_host_analysis_finished(host.name), delay=15,
                 timeout="10m", fail_func=lambda: toolbar.select('Reload'))
        result = host.get_detail('Relationships', 'Availability Zone')
        assert result == 'nova'
