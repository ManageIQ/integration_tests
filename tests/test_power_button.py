import pytest
from unittestzero import Assert

@pytest.fixture
def pick_random_vm_template(mozwebqa, home_page_logged_in):
    vm_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
    vm_pg.find_vm_page(None,'template',True, False)
    return vm_pg

@pytest.mark.nondestructive
class TestPowerButton:        
        
    def test_power_button_shutdown(self, mozwebqa, home_page_logged_in, pick_random_vm_template):
        pick_random_vm_template.power_button.shutdown_and_cancel()
        
    def test_power_button_restart(self, mozwebqa, home_page_logged_in, pick_random_vm_template):
        pick_random_vm_template.power_button.restart_and_cancel()
        
    def test_power_button_power_on(self, mozwebqa, home_page_logged_in, pick_random_vm_template):
        pick_random_vm_template.power_button.power_on_and_cancel()
        
    def test_power_button_power_off(self, mozwebqa, home_page_logged_in, pick_random_vm_template):
        pick_random_vm_template.power_button.power_off_and_cancel()
        
    def test_power_button_suspend(self, mozwebqa, home_page_logged_in, pick_random_vm_template):
        pick_random_vm_template.power_button.suspend_and_cancel()
        
    def test_power_button_reset(self, mozwebqa, home_page_logged_in, pick_random_vm_template):
        pick_random_vm_template.power_button.reset_and_cancel()
