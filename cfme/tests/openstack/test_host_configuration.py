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


@pytest.mark.usefixtures("setup_provider_modscope")
def test_host_configuration(provider, soft_assert):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        host.run_smartstate_analysis()
        wait_for(lambda: is_host_analysis_finished(host.name), delay=15,
                 timeout="10m", fail_func=lambda: toolbar.select('Reload'))
        soft_assert(
            int(host.get_detail("Configuration", "Packages")) > 0,
            'Nodes number of Packages is 0')

        soft_assert(
            int(host.get_detail("Configuration", "Services")) > 0,
            'Nodes number of Services is 0')

        soft_assert(int(host.get_detail("Configuration", "Files")) > 0,
                    'Nodes number of Files is 0')

        # @rrasouli - No patches test yet
        #         soft_assert(get_integer_value(
        #         host.get_detail("Configuration", "Advanced Settings")) > 0,
        #             "Nodes number of Advanced Settings is 0")
