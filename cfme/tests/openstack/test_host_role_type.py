import pytest
from utils import testgen
from cfme.web_ui import Quadicon
from cfme.web_ui import InfoBlock
from cfme.fixtures import pytest_selenium as sel
import re


pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'],
                                         scope='module')


ROLES = ['NovaCompute', 'Controller', 'BlockStorage', 'SwiftStorage',
         'CephStorage']


@pytest.mark.usefixtures("setup_provider_modscope")
def test_host_role_type(provider):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    result = True
    while result:
        for quad in my_quads:
            role_name = str(quad.name)
            role_name = re.search(r'\((\w+)\)', role_name).group(1)
            if role_name not in ROLES:
                result = False
    assert result
