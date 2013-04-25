#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert


@pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive
class TestEvents:
    def test_default_events(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        explore_pg = home_pg.header.site_navigation_menu("Control").sub_navigation_menu("Explorer").click()
        Assert.true(explore_pg.is_the_current_page)
        events_pg = explore_pg.click_on_events()
        Assert.true(self.default_events == events_pg.events_list)

    @property
    def default_events(self):
        # pasted in from running 'print_default_events'
        return ['Datastore Analysis Complete',
        'Datastore Analysis Request',
        'Host Added to Cluster',
        'Host Analysis Complete',
        'Host Analysis Request',
        'Host Auth Changed',
        'Host Auth Error',
        'Host Auth Incomplete Credentials',
        'Host Auth Invalid',
        'Host Auth Unreachable',
        'Host Auth Valid',
        'Host C & U Processing Complete',
        'Host Compliance Check',
        'Host Compliance Failed',
        'Host Compliance Passed',
        'Host Connect',
        'Host Disconnect',
        'Host Removed from Cluster',
        'Mgmt Sys Auth Changed',
        'Mgmt Sys Auth Error',
        'Mgmt Sys Auth Incomplete Credentials',
        'Mgmt Sys Auth Invalid',
        'Mgmt Sys Auth Unreachable',
        'Mgmt Sys Auth Valid',
        'Tag Complete',
        'Tag Parent Cluster Complete',
        'Tag Parent Datastore Complete',
        'Tag Parent Host Complete',
        'Tag Parent Resource Pool Complete',
        'Tag Request',
        'Un-Tag Complete',
        'Un-Tag Parent Cluster Complete',
        'Un-Tag Parent Datastore Complete',
        'Un-Tag Parent Host Complete',
        'Un-Tag Parent Resource Pool Complete',
        'Un-Tag Request',
        'VDI Connecting to Session',
        'VDI Console Login Session',
        'VDI Disconnected from Session',
        'VDI Login Session',
        'VDI Logoff Session',
        'VM Analysis Complete',
        'VM Analysis Failure',
        'VM Analysis Request',
        'VM Analysis Start',
        'VM C & U Processing Complete',
        'VM Clone Complete',
        'VM Clone Start',
        'VM Compliance Check',
        'VM Compliance Failed',
        'VM Compliance Passed',
        'VM Create Complete',
        'VM Delete (from Disk) Request',
        'VM Discovery',
        'VM Guest Reboot',
        'VM Guest Reboot Request',
        'VM Guest Shutdown',
        'VM Guest Shutdown Request',
        'VM Live Migration (VMOTION)',
        'VM Power Off',
        'VM Power Off Request',
        'VM Power On',
        'VM Power On Request',
        'VM Provision Complete',
        'VM Remote Console Connected',
        'VM Removal from Inventory',
        'VM Removal from Inventory Request',
        'VM Renamed Event',
        'VM Reset',
        'VM Reset Request',
        'VM Retired',
        'VM Retirement Warning',
        'VM Settings Change',
        'VM Snapshot Create Complete',
        'VM Snapshot Create Request',
        'VM Snapshot Create Started',
        'VM Standby of Guest',
        'VM Standby of Guest Request',
        'VM Suspend',
        'VM Suspend Request',
        'VM Template Create Complete']
