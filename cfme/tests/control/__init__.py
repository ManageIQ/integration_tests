from cfme.web_ui import flash, toolbar
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


def wait_for_ssa_enabled():
    wait_for(
        lambda: not toolbar.is_greyed('Configuration', 'Perform SmartState Analysis'),
        delay=10, handle_exception=True, num_sec=600, fail_func=lambda: toolbar.select("Reload"))


def do_scan(vm, additional_item_check=None):
    if vm.rediscover_if_analysis_data_present():
        # policy profile assignment is lost so reassign
        vm.assign_policy_profiles(*vm.assigned_policy_profiles)

    def _scan():
        return vm.get_detail(properties=("Lifecycle", "Last Analyzed")).lower()
    original = _scan()
    if additional_item_check is not None:
        original_item = vm.get_detail(properties=additional_item_check)
    vm.smartstate_scan(cancel=False, from_details=True)
    flash.assert_message_contain("Analysis initiated for 1 VM and Instance from the CFME Database")
    logger.info("Scan initiated")
    wait_for(
        lambda: _scan() != original,
        num_sec=600, delay=5, fail_func=lambda: toolbar.select("Reload"))
    if additional_item_check is not None:
        wait_for(
            lambda: vm.get_detail(properties=additional_item_check) != original_item,
            num_sec=120, delay=5, fail_func=lambda: toolbar.select("Reload"))
    logger.info("Scan finished")
