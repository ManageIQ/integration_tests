from random import choice
import dateparser
from traceback import format_exc
from collections import namedtuple

import pytest

from utils import testgen
from utils.blockers import BZ
from utils.ssh import SSHTail
from utils.appliance.implementations.ui import navigate_to

from cfme.web_ui import paginator, toolbar as tb
from cfme.containers.image import Image, list_tbl
from cfme.containers.provider import ContainersProvider
from cfme.configure.tasks import Tasks


pytestmark = [
    pytest.mark.meta(server_roles='+smartproxy'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')

REGISTRIES = (
    pytest.mark.polarion('CMP-9496')('Unknown Image Source'),
    pytest.mark.polarion('CMP-10064')('registry.access.redhat.com')
)
LOG_VERIFICATION_TAGS = ('pod_wait', 'analyze', 'finish')
TESTED_ATTR = namedtuple('TESTED_ATTR', ['table', 'attr', 'verifier'])
TESTED_ATTRIBUTES = (
    TESTED_ATTR('configuration', 'openscap_results', bool),
    TESTED_ATTR('configuration', 'openscap_html', lambda val: val == 'Available'),
    TESTED_ATTR('configuration', 'last_scan', dateparser.parse),
    TESTED_ATTR('compliance', 'status', lambda val: val == 'Compliant'),
    TESTED_ATTR('compliance', 'history', lambda val: val == 'Available')
)


def delete_all_vm_tasks():
    # delete all tasks
    view = navigate_to(Tasks, 'AllTasks')
    view.delete.item_select('Delete All', handle_alert=True)


def verify_log(log, verification_tags):
    """Verify that verification_tags are shown in the log as the pattern below"""
    for tag in verification_tags:
        if 'Scanning::Job#{}'.format(tag) not in log:
            raise Exception('Could not find verification tag in log: {}'
                            .format(tag))


@pytest.mark.meta(blockers=[BZ(1382326), BZ(1408255), BZ(1371896),
                            BZ(1437128, forced_streams=['5.6', '5.7'])])
@pytest.mark.parametrize(('registry'), REGISTRIES)
def test_containers_smartstate_analysis(provider, registry, soft_assert):

    """Smart State analysis functionality check for single container image.
    Steps:
        1. Perform smart state analysis
            Expected: Green message showing: "...Analysis successfully Initiated"
        2. Waiting for analysis finish
            Expected: 'finished'
        3. check task succession in log
            Expected: LOG_VERIFICATION_TAGS are shown in the log
        4. verify that detail was added
            Expected: all RESULT_DETAIL_FIELDS are shown an pass the function"""
    delete_all_vm_tasks()
    navigate_to(Image, 'All')
    tb.select('List View')
    count = list_tbl.row_count()
    if not count:
        pytest.skip('Images table is empty! - cannot perform SSA test -> Skipping...')
    try:
        evm_tail = SSHTail('/var/www/miq/vmdb/log/evm.log')
    except:  # TODO: Should we add a specific exception?
        pytest.skip('Cannot continue test, probably due to containerized appliance\n'
                    'Traceback: \n{}'.format(format_exc()))
    evm_tail.set_initial_file_end()
    relevant_images = []
    paginator.results_per_page(1000)
    for row in list_tbl.rows():
        if row.image_registry.text.lower() == registry.lower():
            relevant_images.append(row)
    if not relevant_images:
        pytest.skip('Images of the following registry not found: {}'
                    .format(registry))
    chosen_row = choice(relevant_images)
    image_obj = Image(chosen_row.name.text, chosen_row.tag.text, provider)
    image_obj.perform_smartstate_analysis(wait_for_finish=True)
    verify_log(evm_tail.raw_string(), LOG_VERIFICATION_TAGS)
    image_obj.summary.reload()
    for tbl, attr, verifier in TESTED_ATTRIBUTES:
        table = getattr(image_obj.summary, tbl)
        if not soft_assert(hasattr(table, attr),
            '{} table has missing attribute \'{}\''.format(tbl, attr)):
            continue
        value = getattr(table, attr).value
        soft_assert(verifier(value),
            '{}.{} attribute has unexpected value ({})'.format(tbl, attr, value))
