import re
import pytest
from random import choice
from traceback import format_exc
from utils import testgen
from utils.version import current_version
from utils.ssh import SSHTail
from utils.appliance.implementations.ui import navigate_to
from cfme.web_ui import InfoBlock
from cfme.configure import tasks
from cfme.containers.image import Image, list_tbl
from cfme.containers.provider import ContainersProvider
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, flash
from cfme.configure.tasks import Tasks, tasks_table
from wait_for import TimedOutError

# CMP - 9496
pytestmark = [
    pytest.mark.meta(server_roles='+smartproxy'),
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


LOG_VERIFICATION_TAGS = ('pod_wait', 'analyze', 'finish')
RESULT_DETAIL_FIELDS = {'Packages': lambda val: int(val) > 0,
                        'OpenSCAP Resultids': len, 'OpenSCAP HTML': len, 'Last scan': len}


def delete_all_vm_tasks():
    # delete all tasks
    navigate_to(Tasks, 'AllVMContainerAnalysis')
    tb.select('Delete Tasks', 'Delete All', invokes_alert=True)
    sel.handle_alert()


def check_log(log, verify_tags):
    """Verify that verify_tags are shown in the log as the pattern below"""
    for tag in verify_tags:
        assert re.findall(r'\n(.+Scanning::Job#{}.+)\n'.format(re.escape(tag)), log)


@pytest.mark.meta(blockers=[1382326, 1406023])
def test_containers_smartstate_analysis(provider, ssh_client):
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
    # step 1
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
    list_tbl.select_rows_by_indexes(choice(range(count)))
    tb.select('Configuration', 'Perform SmartState Analysis', invokes_alert=True)
    sel.handle_alert()
    flash.assert_message_contain('Analysis successfully initiated')
    # step 2
    ssa_timeout = '5M'
    try:
        tasks.wait_analysis_finished('Container image analysis',
                                     'vm', delay=5, timeout=ssa_timeout)
    except TimedOutError:
        pytest.fail('Timeout exceeded, Waited too much time for SSA to finish ({}).'
                    .format(ssa_timeout))
    # Step 3
    check_log(evm_tail.raw_string(), LOG_VERIFICATION_TAGS)
    # Step 4
    time_queued = tasks_table.rows_as_list()[0].updated.text
    tasks_table.click_cell('Updated', value=time_queued)
    for field, verify_func in RESULT_DETAIL_FIELDS.items():
        assert verify_func(InfoBlock.text('Configuration', field))
