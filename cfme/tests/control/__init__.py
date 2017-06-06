from utils import conf, version
from utils.wait import wait_for
from utils.log import logger
from cfme.web_ui import flash, toolbar

vddk_url_map = {
    "5.5": conf.cfme_data.get("basic_info", {}).get("vddk_url").get("v5_5"),
    "6": conf.cfme_data.get("basic_info", {}).get("vddk_url").get("v6_0"),
    "6.5": conf.cfme_data.get("basic_info", {}).get("vddk_url").get("v6_5")
}


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
    flash.assert_message_contain(version.pick({
        version.LOWEST: "Smart State Analysis initiated",
        "5.5": "Analysis initiated for 1 VM and Instance from the CFME Database"}))
    logger.info("Scan initiated")
    wait_for(
        lambda: _scan() != original,
        num_sec=600, delay=5, fail_func=lambda: toolbar.select("Reload"))
    if additional_item_check is not None:
        wait_for(
            lambda: vm.get_detail(properties=additional_item_check) != original_item,
            num_sec=120, delay=5, fail_func=lambda: toolbar.select("Reload"))
    logger.info("Scan finished")
