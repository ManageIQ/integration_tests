import pytest
from unittestzero import Assert

@pytest.fixture
def pick_random_vm_template(mozwebqa, home_page_logged_in):
    vm_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
    found = False
    while not found:
        for quadicon in vm_pg.quadicon_region.quadicons:
            if quadicon.current_state == 'template':
                quadicon.mark_checkbox()
                found = True
                break
        if not found and not vm_pg.paginator.is_next_page_disabled:
            vm_pg.paginator.click_next_page()
        elif not found and vm_pg.paginator.is_next_page_disabled:
            raise Exception("no template found")
    return vm_pg

class TestPowerButton:        
        
    @pytest.mark.nondestructive
    def test_power_button_shutdown(self, mozwebqa, home_page_logged_in, pick_random_vm_template):
        pick_random_vm_template._power_button.shutdown(False)
        Assert.true(pick_random_vm_template.flash.message.startswith("Shutdown Guest initiated"))
        
    @pytest.mark.nondestructive
    def test_power_button_restart(self, mozwebqa, home_page_logged_in, pick_random_vm_template):
        pick_random_vm_template._power_button.restart(False)
        Assert.true(pick_random_vm_template.flash.message.startswith("Restart Guest initiated"))
        
    @pytest.mark.nondestructive
    def test_power_button_power_on(self, mozwebqa, home_page_logged_in, pick_random_vm_template):
        pick_random_vm_template._power_button.power_on(False)
        Assert.true(pick_random_vm_template.flash.message.startswith("Start initiated"))
        
    @pytest.mark.nondestructive
    def test_power_button_power_off(self, mozwebqa, home_page_logged_in, pick_random_vm_template):
        pick_random_vm_template._power_button.power_off(False)
        Assert.true(pick_random_vm_template.flash.message.startswith("Stop initiated"))
        
    @pytest.mark.nondestructive
    def test_power_button_suspend(self, mozwebqa, home_page_logged_in, pick_random_vm_template):
        pick_random_vm_template._power_button.suspend(False)
        Assert.true(pick_random_vm_template.flash.message.startswith("Suspend initiated"))
        
    @pytest.mark.nondestructive
    def test_power_button_reset(self, mozwebqa, home_page_logged_in, pick_random_vm_template):
        pick_random_vm_template._power_button.reset(False)
        Assert.true(pick_random_vm_template.flash.message.startswith("Reset initiated"))
