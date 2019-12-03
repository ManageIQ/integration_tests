from widgetastic.widget import Table as VanillaTable
from widgetastic_patternfly import Button


class DisksButton(Button):
    """Button above DisksTable used to add new disks
    """

    # Relative to DisksTable
    BTN_CONTAINER_LOC = "../h3//td[contains(@align, 'right') and contains(@id, 'buttons_on')]"

    def __locator__(self):
        # Don't EVER do this, unless you are 100% sure that you have to! This is an exception!
        btn_loc = super(DisksButton, self).__locator__()
        loc = "{}/{}//{}".format(self.parent.locator, self.BTN_CONTAINER_LOC, btn_loc)
        return loc


class DisksTable(VanillaTable):
    """Table to add and remove Disks (in VM Reconfigure form)"""

    add_disk_btn = DisksButton("contains", "Add Disk", classes=[Button.PRIMARY])
    cancel_add_btn = DisksButton("contains", "Cancel Add", classes=[Button.DEFAULT])

    def click_add_disk(self):
        """Clicks the Add Disk button attached to the table and returns the new editable row"""
        self.add_disk_btn.click()
        return self[0]

    def click_cancel_add(self):
        """Clicks the Cancel Add button to cancel adding a new row"""
        self.cancel_add_btn.click()


class NetworkAdaptersTable(VanillaTable):
    """Table to add and remove Disks (in VM Reconfigure form)"""

    add_nw_btn = DisksButton("contains", "Add Network", classes=[Button.PRIMARY])
    cancel_add_nw_btn = DisksButton("contains", "Cancel Add", classes=[Button.DEFAULT])

    def click_add_nw_adapter(self):
        """Clicks the Add Network Adapter button attached to the table and
        returns the new editable row
        """
        self.add_nw_btn.click()
        return self[-1]

    def click_cancel_add_nw_adapter(self):
        """Clicks the Cancel Add button to cancel adding a new row"""
        self.cancel_add_nw_btn.click()
