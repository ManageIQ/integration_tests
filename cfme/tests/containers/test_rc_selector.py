import pytest

from cfme.containers.replicator import Replicator
from utils import testgen, version
from cfme.web_ui import CheckboxTable, toolbar as tb
from utils.appliance.implementations.ui import navigate_to
import random
from itertools import chain
from cfme.containers.provider import ContainersProvider


pytestmark = [
    pytest.mark.uncollectif(
        lambda provider: version.current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    [ContainersProvider], scope='function')

# CMP-9973


def test_rc_selector(provider):
    """ This test verifies the data integrity for the
        rs selector table
    """

    navigate_to(Replicator, 'All')
    tb.select('List View')
    list_selectors = provider.mgmt.list_replication_controller_selector()
    list_selectors_values = list(chain.from_iterable(
        [d.values() for d in list_selectors]))
    list_tbl_rc = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    cls_instances = [r.name.text for r in list_tbl_rc.rows()]
    rand_smpl_list = [cls_instances[i] for i in
                      sorted(random.sample(xrange(len(cls_instances)), 1))]

    for name in rand_smpl_list:
        obj = Replicator(name, provider)
        keys = obj.summary.selector.keys
        vals_prop_tbl = []
        for key in keys:
            element = getattr(obj.summary.selector, key)
            vals_prop_tbl.append(element.value)
            assert set(vals_prop_tbl).issubset(list_selectors_values)
