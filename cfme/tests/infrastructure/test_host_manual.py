# -*- coding: utf-8 -*-
"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.manual]


@test_requirements.infra_hosts
def test_host_setting_default_filter():
    """
    Verify the creation and proper functionality of default filters.

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/8h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Select a filter from the accordion that does not have "(Default)" appended to the
               name. Note items displayed.
            3. Click "Select Default" button.
            4. Logout and log back in to CloudForms and navigate back to the Hosts view.
        expectedResults:
            1. Hosts view is displayed with hosts filtered via the Default filter (denoted by
            "(Default)" next to the filter name in the dropdown).
            2. Items displayed in the hosts panel will be filtered based upon the filter
               selected.
            3. "(Default)" will be displayed beside the filter name in the dropdown.
            4. Hosts view will be displayed filtered via the new Default filter.
    """
    pass


@test_requirements.infra_hosts
def test_host_comparison_properties():
    """
    Verify host comparisons view functionality for properties section.

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Select at least 2 hosts by checking the box in upper left of quadicons.
            3. Click "Compare Selected Items" under the "Configuration" dropdown.
            4. Click on "Host Properties(X)" in the Compare Host view.
            5. Click on "Host Properties(X)" again, in the Compare Host view.
            6. Click to expand the "Properties" comparison section, select "Hardware", and click
               "Apply".
            7. Click on "Hardware(X)" in the Compare Host view.
            8. Click on "Hardware(X)" again, in the Compare Host view.
            9. Click to expand the "Properties" comparison section, select "Network Adapters", and
               click "Apply".
            10. Click on "Network Adapters(X)" in the Compare Host view.
            11. Click on the "#X" items that apply to the network adapters.
            12. Click on the "#X" items again that apply to the network adapters.
            13. Click on "Network Adapters(X)" again, in the Compare Host view.
        expectedResults:
            1. Hosts view is displayed with hosts filtered via the Default filter (denoted by
            "(Default)" next to the filter name in the dropdown).
            2. The selected hosts should be displayed with a blue border and checked checkbox.
            3. The "Compare Host / Node" view should be displayed.
               - icons are displayed for all and only selected hosts with hostname displayed
               - one of the quadicons has the host denoted as "(base)" in the hostname
               - host properties row is displayed (default)
               - "% Matched" text or graphs are displayed
               - when 3 or more hosts are displayed, remove icons exist for all non-base hosts.
            4. The row should be expanded to display all of the properties compared. Items that do
               not match the base host should be in blue. There should be X properties
               displayed. Properties for non-base hosts should be in purple/dark blue.
            5. The Host properties should collapse to one row again.
            6. A hardware row should be added to the view for all hosts with % matching graphs
               displayed for non-base hosts.
            7. The row should be expanded and displayed with same requirements as in step 4.
            8. The hardware metrics should collapse to one row again.
            9. A network adapters row should be added to the view for all hosts with % matching
               graphs displayed for non-base hosts.
            10. The row should be expanded and displayed with same requirements as in step 4.
            11. The "#X" individual network adapter rows should be expanded and displayed with
                same requirements as in step 4.
            12. The "#X" individual network adapter rows should collapse to one row again.
            13. The Network Adapters rows should collapse to one row again.
    """
    pass


@test_requirements.infra_hosts
def test_host_comparison_security():
    """
    Verify host comparisons view functionality for security section.
    This is going to be a similar test as test_host_comparison_properties, but for the Security
    Section.

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Select at least 2 hosts by checking the box in upper left of quadicons.
            3. Click "Compare Selected Items" under the "Configuration" dropdown.
            4. Click to select/check the "Security" checkbox in "Comparison Sections".
            5. Click "Apply"
               *If the displayed rows do not have any items (item count is '(0)') the next
               steps do not apply.
            6. If the security rows/sections have sub-items, click on one of the security row items
               (Users, Groups, ...).
            7. Click on the same security item again.
            8. Repeat steps 6 and 7 for all security sub-items.
               *Steps 6 and 7 apply recursively to any sub items of parent sections that may
               exist.
        expectedResults:
            1. Hosts view is displayed with hosts filtered via the Default filter (denoted by
               "(Default)" next to the filter name in the dropdown).
            2. The selected hosts should be displayed with a blue border and checked checkbox.
            3. The "Compare Host / Node" view should be displayed.
               - icons are displayed for all and only selected hosts with hostname displayed
               - one of the quadicons has the host denoted as "(base)" in the hostname
               - host properties row is displayed (default)
               - "% Matched" text or graphs are displayed
               - when 3 or more hosts are displayed, remove icons exist for all non-base hosts.
            4. "Security" in comparison sections should turn blue.
            5. New rows should be displayed in the compare host/node view for all security items
               (Users, Groups, Firewall Rules). The new rows should have the following:
               - "% Matched" text or graphs are displayed
               - sub-items that are not empty should have the ">" displayed and be able to be
            expanded.
            6. The security row/section should be expanded, displaying all sub-items in the
               section.
               - Items that do not match the base host should be in blue.
               - The number of properties displayed should match the number denoted on the
                 parent row.
               - Properties for non-base hosts should be in purple/dark blue.
            7. The section should collapse again to only display the parent row.
            8. Same expected results as for step 6 and 7.
    """
    pass


@test_requirements.infra_hosts
def test_host_comparison_configuration():
    """
    Verify host comparisons view functionality for configuration section.
    This is going to be similar as test_host_comparison_security, but for the Configuration
    Section.

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Select at least 2 hosts (three if possible) by checking the box in upper left of
               host quadicons.
            3. Click "Compare Selected Items" under the "Configuration" dropdown.
            4. Click to select/check the "Configuration" checkbox in "Comparison Sections".
            5. Click "Apply"
               *If the displayed rows do not have any items (item count is '(0)') the next
               steps do not apply.
            6. If the configuration rows/sections have sub-items, click on one of the configuration
               row items (OS, Guest Applications, ...).
            7. Click on the same configuration item again.
            8. Repeat steps 6 and 7 for all configuration sub-items.
               *Steps 6 and 7 apply recursively to any sub items of parent sections that may exist.
        expectedResults:
            1. Hosts view is displayed with hosts filtered via the Default filter (denoted by
               "(Default)" next to the filter name in the dropdown).
            2. The selected hosts should be displayed with a blue border and checked checkbox.
            3. The "Compare Host / Node" view should be displayed.
               - icons are displayed for all and only selected hosts with hostname displayed
               - one of the quadicons has the host denoted as "(base)" in the hostname
               - host properties row is displayed (default)
               - "% Matched" text or graphs are displayed
               - when 3 or more hosts are displayed, remove icons exist for all non-base hosts.
            4. "Configuration" in comparison sections should turn blue.
            5. New rows should be displayed in the compare host/node view for all configuration
               items (OS, Guest Applications, ...). The new rows should have the following:
               - "% Matched" text or graphs are displayed
               - sub-items that are not empty should have the ">" displayed and be able to be
               expanded.
            6. The configuration row/section should be expanded, displaying all sub-items in the
               section.
               - Items that do not match the base host should be in blue.
               - The number of properties displayed should match the number denoted on the parent
                 row.
               - Properties for non-base hosts should be in purple/dark blue.
            7. The section should collapse again to only display the parent row.
            8. Same expected results as for step 6 and 7.
    """
    pass


@test_requirements.infra_hosts
def test_host_comparison_my_company_tags():
    """
    Verify host comparisons view functionality for 'My Company Tags' section.
    This is going to be the same test as test_host_comparison_properties, but for the "My Company
    Tags" section.

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Select at least 2 hosts (three if possible) by checking the box in upper left of
               host quadicons.
            3. Click "Compare Selected Items" under the "Configuration" dropdown.
            4. Click to select/check the "My Company Tags" checkbox in "Comparison Sections".
            5. Click "Apply"
               *If the displayed rows do not have any items (item count is '(0)') the next
               steps do not apply.
            6. If the "My Company Tags" rows/sections have sub-items, click on one of the "My
               Company Tags" row items (Department, Customer, ...).
            7. Click on the same "My Company Tags" item again.
            8. Repeat steps 6 and 7 for all "My Company Tags" sub-items.
               *Steps 6 and 7 apply recursively to any sub items of parent sections that may
               exist.
        expectedResults:
            1. Hosts view is displayed.
            2. The selected hosts should be displayed with a blue border and checked checkbox.
            3. The "Compare Host / Node" view should be displayed.
               - icons are displayed for all and only selected hosts with hostname displayed
               - one of the quadicons has the host denoted as "(base)" in the hostname
               - host properties row is displayed (default)
               - "% Matched" text or graphs are displayed
               - when 3 or more hosts are displayed, remove icons exist for all non-base hosts.
            4. "My Company Tags" in comparison sections should turn blue.
            5. New rows should be displayed in the compare host/node view for all "My Company Tags"
               items (Department, Customer, ...). The new rows should have the following:
               - "% Matched" text or graphs are displayed
               - sub-items that are not empty should have the ">" displayed and be able to be
                 expanded.
            6. The "My Company Tags" row/section should be expanded, displaying all sub-items in
               the section.
               - Items that do not match the base host should be in blue.
               - The number of properties displayed should match the number denoted on the parent
                 row.
               - Properties for non-base hosts should be in purple/dark blue.
            7. The section should collapse again to only display the parent row.
            8. Same expected results as for step 6 and 7.
    """
    pass


@test_requirements.infra_hosts
def test_host_comparison_remove_hosts():
    """
    Test removing hosts from the "Compare Host / Node" view.

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Select at least 3 hosts (more if possible) by checking the box in upper left of
               quadicons.
            3. Click "Compare Selected Items" under the "Configuration" dropdown.
            4. Click on the remove icon (trash can) on one of the hosts.
            5. If hosts still exist with the remove icon displayed, click on one.
            6. Repeat step 5 until only 2 hosts remain.
        expectedResults:
            1. Hosts view is displayed.
            2. The selected hosts should be displayed with a blue border and checked checkbox.
            3. The "Compare Host / Node" view should be displayed.
               - icons are displayed for all and only selected hosts with hostname displayed
               - one of the quadicons has the host denoted as "(base)" in the hostname
               - host properties row is displayed (default)
               - "% Matched" text or graphs are displayed
               - remove icons exist for all non-base hosts.
            4. The clicked host should be removed from display.
               - The same host is still denoted as the base host.
               - when, and only when, 3 or more hosts are displayed, remove icons exist for all
                 non-base hosts.
            5. The clicked host should be removed from display.
               - The same host is still denoted as the base host.
               - when, and only when, 3 or more hosts are displayed, remove icons exist for all
                 non-base hosts.
            6. Hosts should be displayed without the remove host icon.
    """
    pass


@test_requirements.infra_hosts
def test_host_comparison_exists_mode():
    """
    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Select at least 3 hosts (more if possible) by checking the box in upper left of
               quadicons.
            3. Click "Compare Selected Items" under the "Configuration" dropdown.
            4. Select "Network Adapters" from the compare section accordion and click "Apply".
            5. Click on the "Network Adapters" row, in the Compare Host/Node view, to expand it.
            6. Click the "Exists Mode" icon (in row of buttons to top left).
        expectedResults:
            1. Hosts view is displayed.
            2. The selected hosts should be displayed with a blue border and checked checkbox.
            3. The "Compare Host / Node" view should be displayed (in expanded view by default).
               - icons are displayed for all and only selected hosts with hostname displayed
               - one of the quadicons has the host denoted as "(base)" in the hostname
               - host properties row is displayed (default)
               - "% Matched" text or graphs are displayed
               - remove icons exist for all non-base hosts.
            4. Network Adapter row will be displayed in the Compare Host/Node panel.
            5. Individual child rows will be displayed with "% Matched" in base host and graphs
               displayed for the rest of the hosts.
            6. The "% Matched" and graphs displayed on child rows will be replaced with "+" or
                  "-" depending if the item exists in the non-base hosts.
    """
    pass


@test_requirements.infra_hosts
def test_host_comparison_compressed_view():
    """
    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Select at least 3 hosts (more if possible) by checking the box in upper left of
               quadicons.
            3. Click "Compare Selected Items" under the "Configuration" dropdown.
            4. Click the "Compressed View" icon (in row of buttons to top left).
        expectedResults:
            1. Hosts view is displayed with hosts filtered via the Default filter (denoted by
               "(Default)" next to the filter name in the dropdown).
            2. The selected hosts should be displayed with a blue border and checked checkbox.
            3. The "Compare Host / Node" view should be displayed (in expanded view by
               default).
               - icons are displayed for all and only selected hosts with hostname displayed
               - one of the quadicons has the host denoted as "(base)" in the hostname
               - host properties row is displayed (default)
               - "% Matched" text or graphs are displayed
               - remove icons exist for all non-base hosts.
            4. All hosts are still displayed but now in compressed mode:
               - column headings(hosts) are displayed vertically
               - a smaller, simpler, icon is displayed (represents 3rd quadrant) for the hosts.
               - on parent rows, "% Matched" is displayed as "%".
               - on child(leaf) rows, color coded values are replaced with checkmarks for
                 matching, and x's for non-matching values
    """
    pass


@test_requirements.infra_hosts
def test_host_comparison_report():
    """
    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Select at least 3 hosts (more if possible) by checking the box in upper left of
               quadicons.
            3. Click "Compare Selected Items" under the "Configuration" dropdown.
            4. Click "Download as text" under the Downloads pulldown.
            5. Click "Download as CSV" under the Downloads pulldown.
            6. Click "Print or export as PDF".
        expectedResults:
            1. Hosts view is displayed.
            2. The selected hosts should be displayed with a blue border and checked checkbox.
            3. The "Compare Host / Node" view should be displayed.
            4. A compare report should be downloaded (Chrome will show it in left bottom
               corner of window.
               - report is in text format.
               - report has date appended to name.
               - data in the report matches the GUI.
            5. A compare report should be downloaded (Chrome will show it in left bottom
               corner of window.
               - report is in CSV format.
               - report has date appended to name.
               - data in the report matches the GUI.
            6. A print page is displayed containing the compare report.
    """
    pass


@test_requirements.infra_hosts
def test_host_comparison_multipleviews_interactions():
    """
    Here i will test adding and removing rows and sections in permutations I did not cover
    explictily already. Also cover the case where clicking on the parent section selects all of
    the child sections.

    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Select at least 3 hosts (more if possible) by checking the box in upper left
               of quadicons.
            3. Click "Compare Selected Items" under the "Configuration" dropdown.
            4. Click to select "My Company Tags" in the Comparison Sections dropdown,
               and click "Apply".
            5. Repeat step 4 for Configuration, Security, and Properties sections.
               Note: Properties will need to be clicked twice as it defaults to checked
               with only one section enbled.
            6. Click on "My Company Tags" in Comparison Sections dropdown.
            7. Click on a child item, to deselect, and click "Apply".
            8. Click on random child items within the section and click "Apply" until no
               child items remain selected.
            9. Click on random child items within the section and click "Apply" until all
               child items remain selected.
            10. Repeat steps 6 through 9 for Configuration, Security, and Properties
                sections.
        expectedResults:
            1. Hosts view is displayed.
            2. The selected hosts should be displayed with a blue border and checked
               checkbox.
            3. The "Compare Host / Node" view should be displayed.
            4. All of the "My Company Togs" sections are displayed in Compare Host/Node
               panel.
            5. All of the sections for selected parent are displayed in Compare Host/Node
               panel.
            6. Expanded section will be displayed with all child items.
            7. Child item is removed from display in Compare Hosts/Node panel.
            8. Each child item is removed from display in Compare Hosts/Node panel.
            9. Each child item is added to display in Compare Hosts/Node panel.
            10. Same expected results as for steps 6 through 9.
    """
    pass


@test_requirements.infra_hosts
def test_host_refresh_multiple():
    """
    Testing refreshing multiple hosts.


    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Select at least 2 hosts (more if possible) by checking the box in upper left of
               quadicons.
            3. Click "Refresh Relationships and Power States" under the Configuration
               dropdowm, and then click "OK" when prompted.
        expectedResults:
            1. Hosts view is displayed.
            2. The selected hosts should be displayed with a blue border and checked checkbox.
            3. "Refresh initiated for X Hosts from the CFME Database" is displayed in green
               banner where "X" is the number of selected hosts. Properties for each host are
               refreshed.
    """
    pass


@test_requirements.infra_hosts
def test_host_discover_multiple_valid_ips():
    """
    Testing discovering multiple hosts (not using providers).


    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Click "Discover Items" under the Configuration accordion.
            3. Click the checkbox to select "ESX".
            4. In the Subnet Range section, enter a valid ip range for existing, undiscovered hosts
               and click "Start" button.
            5. Repeat steps 1 through 4 but select "IPMI"in step 3.
        expectedResults:
            1. Hosts view is displayed.
            2. The "Hosts/Nodes Discovery" view is displayed.
            3.
            4. When available, the new hosts display. They are named by hostname and IP address.
            5. Same expected results as for steps 1 through 4.
    """
    pass


@test_requirements.infra_hosts
def test_host_removal():
    """
    Testing removing a host.


    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Click checkbox to select host(s).
            3. Click "Remove items from inventory" in the Configuration accordion.
            4. Click OK.
        expectedResults:
            1. Hosts view is displayed.
            2.
            3.
            4. The host(s) is/are removed. The virtual machines remain in the VMDB, but are no
               longer associated with their respective hosts.
    """
    pass


@test_requirements.infra_hosts
def test_host_refresh():
    """
    Testing refreshing single host.


    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Select a host by checking the box in upper left of quadicons.
            3. Click "Refresh Relationships and Power States" under the Configuration dropdowm,
               and then click "OK" when prompted.
        expectedResults:
            1. Hosts view is displayed.
            2. The selected hosts should be displayed with a blue border and checked checkbox.
            3. "Refresh initiated for 1 Host from the CFME Database" is displayed in green
               banner. Properties for each host are refreshed.
    """
    pass


@test_requirements.infra_hosts
def test_host_view_device_info():
    """
    Testing the viewing of host device information.


    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Click on a Host.
            3. From the host accordion, click Properties > Devices.
        expectedResults:
            1. Hosts view is displayed.
            2. The summary view is displayed for the host.
            3. The Device view is displayed.
    """
    pass


@test_requirements.infra_hosts
def test_host_view_network_info():
    """
    Testing the viewing of host network information.


    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Click on a Host.
            3. From the host accordion, click Properties > Network.
        expectedResults:
            1. Hosts view is displayed.
            2. The summary view is displayed for the host.
            3. The Network view is displayed.
    """
    pass


@test_requirements.infra_hosts
def test_host_view_storage_adapter():
    """
    Testing the viewing of storage adapters.


    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Click on a Host.
            3. From the host accordion, click Properties > Storage Adapters.
        expectedResults:
            1. Hosts view is displayed.
            2. The summary view is displayed for the host.
            3. The Storage adapters view is displayed with asscoaited VMs, targets and LUNs.
    """
    pass


@test_requirements.infra_hosts
def test_host_viewing():
    """
    Testing the viewing of host info.


    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Click on a host quadicon.
        expectedResults:
            1. Hosts view is displayed.
            2. The hosts summary view is displayed containing taskbar, summary panel,
               accordion, and print/export button.
               - Items in the accordion sections are displayed in view panel when clicked.
               - Print/export view is displayed when print/export button is clicked.
               - Row items that are blue on mouseover can be clicked and display additional
                 details when done so.
    """
    pass


@test_requirements.infra_hosts
def test_host_tagging():
    """
    Testing tagging hosts.


    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/4h
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Click checkbox in quadicon to select a host.
            3. Click Edit Tags in the Policy dropdown.
            4. Select a customer tag from the first dropdown and then a value for the tag.
            5. Click save.
            6. Click on the same quadicon as in step 2.
            7. Repeat steps 1 thru 6, but select multiple hosts.
        expectedResults:
            1. Hosts view is displayed.
            2.
            3. Tag Assignement view is displayed.
            4.
            5. "Tag edits successfully saved." message is displayed.
            6. Tags added in step 4 are displayed in Smart Management section of hosts summary.
            7. Expected results are the same as steps 1 thru 6 for multiple hosts.
    """
    pass


@test_requirements.infra_hosts
def test_host_drift_analysis():
    """
    Testing drift detection for hosts.


    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        setup:
            1. At least 2 Smart State Analysis(SSA) tasks must have been executed on the host
               used below.
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Click checkbox in quadicon to select a host.
            3. Click on Drift History in the Relationships accordion
            4. Select at least 2 items in the Drift History view.
            5. Click the drift analysis button (top left corner below breadcrumbs).
            6. Click to expand the Host Properties row.
            7. Click on compressed view icon.
            8. Click on Network Adapters under Properties in Drift Sections and click "Apply".
            9. Click to expand Network Adapters row in the Drift Analyssis view.
            10. Click Exists Mode button, and Expanded View button.
            11. Click "Attributes with same values" button in the toolbar.
            12. Click "Attributes with different values" button in the toolbar.
        expectedResults:
            1. Hosts view is displayed.
            2. Summary view is displayed.
            3. Drift History view is displayed.
            4.
            5. Drift Analysis view is displayed.
            6. All Host Properties rows are displayed, populated with appropriate data. Parent
               rows have a check in cells with all matching data between hosts and a delta icon
               where the data differs.
            7. Specific item data is replaced with associated check or delta icons.
            8. Network Adapters row is added to Drift Analysis.
            9. All Network Adapters rows are displayed, populated with appropriate data. Parent
               rows have a check in cells with all matching data between hosts and a delta icon
               where the data differs.
            10. Cell data for non-base hosts displayed with pluses or minus icon base on
                existance of item.
            11. Only attributes matching across hosts are displayed.
            12. Only attributes not matching across hosts are displayed.

    """
    pass


@test_requirements.infra_hosts
def test_host_drift_reports():
    """
    Testing drift analysis reports for hosts.


    Polarion:
        assignee: prichard
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        setup:
            1. At least 2 Smart State Analysis(SSA) tasks must have been executed on the host
               used below.
        testSteps:
            1. Navigate to the Compute > Infrastructure > Hosts view.
            2. Click checkbox in quadicon to select a host.
            3. Click on Drift History in the Relationships accordion
            4. Select at least 2 items in the Drift History view.
            5. Click the drift analysis button (top left corner below breadcrumbs).
            6. Click "Download As Text" under Download dropdown.
            7. Click "Download As CSV" under Download dropdown.
            8. Click "Print or export as PDF" under Download dropdown.
        expectedResults:
            1. Hosts view is displayed.
            2. Summary view is displayed.
            3. Drift History view is displayed.
            4.
            5. Drift Analysis view is displayed.
            6. Drift report is downloaded in text format.
            7. Drift report is downloaded in CSV format.
            8. "Print" window/tab is displayed for drift report.
    """
    pass
