#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert


@pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive
class TestActions:
    def test_default_actions(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        explore_pg = home_pg.header.site_navigation_menu("Control").sub_navigation_menu("Explorer").click()
        Assert.true(explore_pg.is_the_current_page)
        actions_pg = explore_pg.click_on_actions()
        Assert.true(self.default_actions == actions_pg.actions_list)

    def test_create_invalid_action(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        explore_pg = home_pg.header.site_navigation_menu("Control").sub_navigation_menu("Explorer").click()
        Assert.true(explore_pg.is_the_current_page)
        actions_pg = explore_pg.click_on_actions()
        Assert.true(actions_pg.is_the_current_page)
        new_actions_pg = actions_pg.click_on_add_new()
        new_actions_pg = new_actions_pg.add_invalid_action()
        Assert.true(new_actions_pg.flash.message == "Action Type must be selected")

    @property
    def default_actions(self):
        # pasted in from running 'print_default_actions'
        return [('Cancel vCenter Task', 'Cancel vCenter Task'),
        ('Check Host or VM Compliance', 'Check Host or VM Compliance'),
        ('Collect Running Processes on VM Guest OS', 'Collect Running Processes on VM Guest OS'),
        ('Connect All CD-ROM Drives for Virtual Machine', 'Connect All CD-ROM Drives for Virtual Machine'),
        ('Connect All Floppy and CD-ROM Drives for Virtual Machine', 'Connect All Floppy and CD-ROM Drives for Virtual Machine'),
        ('Connect All Floppy Drives for Virtual Machine', 'Connect All Floppy Drives for Virtual Machine'),
        ('Convert to Template', 'Convert to Template'),
        ('Delete all Snapshots', 'Delete all Snapshots'),
        ('Delete Most Recent Snapshot', 'Delete Most Recent Snapshot'),
        ('Delete VM from Disk', 'Delete VM from Disk'),
        ('Disconnect All CD-ROM Drives for Virtual Machine', 'Disconnect All CD-ROM Drives for Virtual Machine'),
        ('Disconnect All Floppy and CD-ROM Drives for Virtual Machine', 'Disconnect All Floppy and CD-ROM Drives for Virtual Machine'),
        ('Disconnect All Floppy Drives for Virtual Machine', 'Disconnect All Floppy Drives for Virtual Machine'),
        ('Execute an external script', 'Execute an external script'),
        ('Generate Audit Event', 'Generate Audit Event'),
        ('Generate log message', 'Generate log message'),
        ('Initiate SmartState Analysis for Host', 'Initiate SmartState Analysis for Host'),
        ('Initiate SmartState Analysis for VM', 'Initiate SmartState Analysis for VM'),
        ('Invoke A Custom Automation', 'Invoke A Custom Automation'),
        ('Mark as Non-Compliant', 'Mark as Non-Compliant'),
        ('Prevent current event from proceeding', 'Prevent current event from proceeding'),
        ('Put Virtual Machine Guest OS in Standby', 'Put Virtual Machine Guest OS in Standby'),
        ('Raise Automation Event', 'Raise Automation Event'),
        ('Refresh data from vCenter', 'Refresh data from vCenter'),
        ('Remove Virtual Machine from Inventory', 'Remove Virtual Machine from Inventory'),
        ('Retire Virtual Machine', 'Retire Virtual Machine'),
        ('Show EVM Event on Timeline', 'Show EVM Event on Timeline'),
        ('Shutdown Virtual Machine Guest OS', 'Shutdown Virtual Machine Guest OS'),
        ('Start Virtual Machine', 'Start Virtual Machine'),
        ('Stop Virtual Machine', 'Stop Virtual Machine'),
        ('Suspend Virtual Machine', 'Suspend Virtual Machine')]
