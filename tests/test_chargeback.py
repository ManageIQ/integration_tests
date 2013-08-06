import pytest
from unittestzero import Assert


@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestChargeback():

    def test_chargeback(self, vi_chargeback_pg):
        #Add a new Compute Chargeback
        Assert.true(vi_chargeback_pg.is_the_current_page)
        rates_pg = vi_chargeback_pg.click_on_rates()
        compute_pg = rates_pg.click_on_compute()
        add_compute_chargeback_pg = compute_pg\
                .click_on_add_new_chargeback_rate()
        Assert.true(add_compute_chargeback_pg.alloc_cpu_input)
        add_compute_chargeback_pg.click_on_cancel()
        
        #Add a new Storage Chargeback
        storage_pg = rates_pg.click_on_storage()
        add_storage_chargeback_pg = storage_pg\
                .click_on_add_new_chargeback_rate()
        Assert.true(add_storage_chargeback_pg.alloc_disk_storage_input)
        add_storage_chargeback_pg.click_on_cancel()

        #Edit Compute Chargeback
        compute_pg = rates_pg.click_on_compute()
        existing_chargeback = "Default"
        selected_chargeback_pg = compute_pg\
                .click_on_existing_chargeback(existing_chargeback)
        # remove_selected_chargeback_pg = selected_chargeback_pg\
        #        .click_on_remove()
        edit_selected_chargeback_pg = selected_chargeback_pg.click_on_edit()
        Assert.true(edit_selected_chargeback_pg.description_input\
                .get_attribute("value") == "Default")
        Assert.true(edit_selected_chargeback_pg.alloc_cpu_input)
        edit_selected_chargeback_pg.click_on_cancel()


        #Edit Storage Chargeback
        storage_pg = rates_pg.click_on_storage()
        existing_chargeback = "Default"
        selected_chargeback_pg = storage_pg\
                .click_on_existing_chargeback(existing_chargeback)
        # remove_selected_chargeback_pg = selected_chargeback_pg\
        #        .click_on_remove()
        edit_selected_chargeback_pg = selected_chargeback_pg.click_on_edit()
        Assert.true(edit_selected_chargeback_pg.description_input\
                .get_attribute("value") == "Default")
        Assert.true(edit_selected_chargeback_pg.alloc_disk_storage_input)
        edit_selected_chargeback_pg.click_on_cancel()


