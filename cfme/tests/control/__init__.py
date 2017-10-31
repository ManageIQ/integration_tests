from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


def wait_for_ssa_enabled(vm):
    """Waits for "Perform SmartState Analysis" item enabled for a vm

    Args:
        vm (BaseVM): a vm object
    """
    vm_details_view = navigate_to(vm, "Details")
    wait_for(
        vm_details_view.toolbar.configuration.item_enabled,
        func_args=["Perform SmartState Analysis"],
        delay=10,
        handle_exception=True,
        num_sec=300,
        fail_func=vm_details_view.toolbar.reload.click
    )


def do_scan(vm, additional_item_check=None, rediscover=True):
    vm_details_view = navigate_to(vm, "Details")
    if rediscover:
        if vm.rediscover_if_analysis_data_present():
            # policy profile assignment is lost so reassign
            vm.assign_policy_profiles(*vm.assigned_policy_profiles)

    def _scan():
        return vm.get_detail(properties=("Lifecycle", "Last Analyzed")).lower()
    original = _scan()
    if additional_item_check is not None:
        original_item = vm.get_detail(properties=additional_item_check)
    vm.smartstate_scan(cancel=False, from_details=True)
    vm_details_view.flash.assert_success_message(
        "Analysis initiated for 1 VM and Instance from the CFME Database")
    logger.info("Scan initiated")
    wait_for(
        lambda: _scan() != original,
        num_sec=300, delay=5, fail_func=vm_details_view.toolbar.reload.click)
    if additional_item_check is not None:
        wait_for(
            lambda: vm.get_detail(properties=additional_item_check) != original_item,
            num_sec=120, delay=5, fail_func=vm_details_view.toolbar.reload.click)
    logger.info("Scan finished")
