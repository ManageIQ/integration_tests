import re
from random import choice
import pytest
from utils import testgen
from utils.version import current_version
from utils.ssh import SSHTail
from utils.appliance.implementations.ui import navigate_to
from cfme.web_ui import InfoBlock
from cfme.configure import tasks
from cfme.containers.image import Image
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import paginator, toolbar as tb, CheckboxTable, flash
from traceback import format_exc

# CMP - 9496
pytestmark = [
    pytest.mark.meta(server_roles='+smartproxy'),
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
tasks_tbl = CheckboxTable(table_locator="//table[@class='table table-striped "
                          "table-bordered table-hover table-selectable']")

LOG_VERIFICATION_TAGS = ('pod_wait', 'analyze', 'finish')
RESULT_DETAIL_FIELDS = {'Packages': lambda val: int(val) > 0,
                        'OpenSCAP Resultids': len, 'OpenSCAP HTML': len, 'Last scan': len}


def _wait_all_tasks_finished():
    # wait until all tasks are finished
    if tasks.all_vm_analysis_tasks():
        tasks.wait_analysis_finished(tasks.all_vm_analysis_tasks()[0]['task_name'], 'vm',
                                     delay=5, timeout='5M')


def check_log(log, verify_tags):
    """Verify that verify_tags are shown in the log as the pattern below"""
    for tag in verify_tags:
        assert re.findall(r'\n(.+Scanning::Job#{}.+)\n'.format(re.escape(tag)), log)


def test_containers_smartstate_analysis(ssh_client):
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
    # step 1
    navigate_to(Image, 'All')
    count = paginator.rec_total()
    if not count:
        pytest.fail('No Containers to test!')
    tb.select('List View')
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
    # asserting  Task was started
    # step 2
    _wait_all_tasks_finished()
    # Step 3
    check_log(evm_tail.raw_string(), LOG_VERIFICATION_TAGS)
    # Step 4
    time_queued = tasks_tbl.rows_as_list()[0].updated.text
    tasks_tbl.click_cell('Updated', value=time_queued)
    for field, verify_func in RESULT_DETAIL_FIELDS.items():
        assert verify_func(InfoBlock.text('Configuration', field))
