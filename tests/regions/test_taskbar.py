'''
Created on Feb 28, 2013

@author: bcrochet
'''

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestTaskbar:
    def test_history_buttons(self, infra_vms_pg):
        history_buttons = infra_vms_pg.history_buttons
        history_buttons.refresh_button.click()

    def test_view_buttons(self, infra_vms_pg):
        view_buttons = infra_vms_pg.view_buttons
        Assert.true(view_buttons.is_grid_view, "Not default grid view")
        view_buttons.change_to_tile_view()
        Assert.true(view_buttons.is_tile_view, "Not tile view")
        view_buttons.change_to_list_view()
        Assert.true(view_buttons.is_list_view, "Not list view")
        view_buttons.change_to_grid_view()
        Assert.true(view_buttons.is_grid_view, "Not grid view")

