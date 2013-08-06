import pytest
from unittestzero import Assert

@pytest.fixture
def pick_random_vm_template(infra_vms_pg):
    infra_vms_pg.find_vm_page(None,'template',True, False)
    return infra_vms_pg

# TODO: Need some asserts here

@pytest.mark.nondestructive
class TestPowerButton:

    def test_power_button_shutdown(self, pick_random_vm_template):
        pick_random_vm_template.power_button.shutdown_and_cancel()

    def test_power_button_restart(self, pick_random_vm_template):
        pick_random_vm_template.power_button.restart_and_cancel()

    def test_power_button_power_on(self, pick_random_vm_template):
        pick_random_vm_template.power_button.power_on_and_cancel()

    def test_power_button_power_off(self, pick_random_vm_template):
        pick_random_vm_template.power_button.power_off_and_cancel()

    def test_power_button_suspend(self, pick_random_vm_template):
        pick_random_vm_template.power_button.suspend_and_cancel()

    def test_power_button_reset(self, pick_random_vm_template):
        pick_random_vm_template.power_button.reset_and_cancel()
