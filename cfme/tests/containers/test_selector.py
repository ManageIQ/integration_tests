import pytest

from itertools import chain
from cfme.containers.provider import ContainersProvider, navigate_and_get_rows
from cfme.containers.replicator import Replicator as Rc
from utils import testgen, version
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.uncollectif(
        lambda provider: version.current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    [ContainersProvider], scope='function')


@pytest.mark.polarion('CMP-9973')
def test_rc_selector(provider, soft_assert):
    """ This test verifies the data integrity for the
        rc selectors table
    """

    navigate_to(Rc, 'All')

    list_selectors_api = provider.mgmt.list_replication_controller_selector()
    list_selectors_values_api = list(chain.from_iterable(
        [d.values() for d in list_selectors_api]))
    rows = navigate_and_get_rows(provider, Rc, 2)
    rc_names = [r.name.text for r in rows]

    for name in rc_names:
        obj = Rc(name, provider)
        keys = obj.summary.selector.keys
        vals_prop_tbl_ui = []
        for key in keys:
            element = getattr(obj.summary.selector, key)
            vals_prop_tbl_ui.append(element.value)
            soft_assert(
                set(vals_prop_tbl_ui).issubset(list_selectors_values_api),
                "Selectors table for rc object was not validated")
