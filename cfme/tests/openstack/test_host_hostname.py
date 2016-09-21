from utils import testgen
from cfme.web_ui import Quadicon, toolbar
from cfme.infrastructure.host import Host
from cfme.configure.tasks import is_host_analysis_finished
from utils.wait import wait_for
import pytest

pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'], scope='module')
pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


def test_host_hostname(provider):
    provider.summary.relationships.nodes.click()
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        host.run_smartstate_analysis()
        wait_for(lambda: is_host_analysis_finished(host.name), delay=15,
                 timeout="10m", fail_func=lambda: toolbar.select('Reload'))
        result = host.get_detail("Properties", "Hostname")
        assert result != ''
