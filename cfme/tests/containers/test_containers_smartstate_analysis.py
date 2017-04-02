import dateparser
from traceback import format_exc
from collections import namedtuple

import pytest

from cfme.containers.image import Image
from cfme.containers.provider import ContainersProvider, ContainersTestItem,\
    navigate_and_get_rows

from utils.log_validator import LogValidator
from utils import testgen
from utils.blockers import BZ


pytestmark = [
    pytest.mark.meta(server_roles='+smartproxy'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')

LOG_VERIFICATION_VERBS = ('pod_create', 'pod_wait', 'pod_delete', 'analyze', 'finish')

TestedAttr = namedtuple('TestedAttr', ['table', 'attr', 'verifier'])

TESTED_ATTRIBUTES__openscap_off = (
    TestedAttr('configuration', 'openscap_results', bool),
    TestedAttr('configuration', 'openscap_html', lambda val: val == 'Available'),
    TestedAttr('configuration', 'last_scan', dateparser.parse)
)
TESTED_ATTRIBUTES__openscap_on = TESTED_ATTRIBUTES__openscap_off + (
    TestedAttr('compliance', 'status', lambda val: val.startswith('Compliant')),
    TestedAttr('compliance', 'history', lambda val: val == 'Available')
)

TEST_ITEMS = (
    pytest.mark.polarion('CMP-9496')(
        ContainersTestItem(Image, 'CMP-9496',
                           is_openscap=False,
                           tested_attr=TESTED_ATTRIBUTES__openscap_off)
    ),
    pytest.mark.polarion('CMP-10064')(
        ContainersTestItem(Image, 'CMP-10064',
                           is_openscap=True,
                           tested_attr=TESTED_ATTRIBUTES__openscap_on)
    )
)


@pytest.mark.meta(blockers=[BZ(1382326), BZ(1408255), BZ(1371896),
                            BZ(1437128, forced_streams=['5.6', '5.7'])])
@pytest.mark.parametrize(('test_item'), TEST_ITEMS)
def test_containers_smartstate_analysis(provider, test_item, soft_assert):

    chosen_row = navigate_and_get_rows(provider, Image, 1)[0]
    image_obj = Image(chosen_row.name.text, chosen_row.tag.text, provider)

    if test_item.is_openscap:
        image_obj.assign_policy_profiles('OpenSCAP profile')
    else:
        image_obj.unassign_policy_profiles('OpenSCAP profile')

    try:
        evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                                matched_patterns=LOG_VERIFICATION_VERBS)
    except:  # TODO: Should we add a specific exception?
        pytest.skip('Cannot continue test, probably due to containerized appliance\n'
                    'Traceback: \n{}'.format(format_exc()))

    evm_tail.fix_before_start()

    image_obj.perform_smartstate_analysis(wait_for_finish=True)

    image_obj.summary.reload()
    for tbl, attr, verifier in test_item.tested_attr:

        table = getattr(image_obj.summary, tbl)

        if not soft_assert(hasattr(table, attr),
                '{} table has missing attribute \'{}\''.format(tbl, attr)):
            continue
        value = getattr(table, attr).value
        soft_assert(verifier(value),
            '{}.{} attribute has unexpected value ({})'.format(tbl, attr, value))
