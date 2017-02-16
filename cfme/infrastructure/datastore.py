""" A model of an Infrastructure Datastore in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Datastores pages.
"""
from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.exceptions import CandidateNotFound, ListAccordionLinkNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    Quadicon, Region, listaccordion as list_acc, toolbar as tb,
    flash, InfoBlock, match_location, fill, paginator, accordion
)
from cfme.web_ui.form_buttons import FormButton
from utils import version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.pretty import Pretty
from utils.providers import get_crud
from utils.wait import wait_for


details_page = Region(infoblock_type='detail')

page_title_loc = '//div[@id="center_div" or @id="main-content"]//h1'

default_datastore_filter_btn = FormButton('Set the current filter as my default')

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')

match_page = partial(match_location, controller='storage',
                     title='Datastores')

# todo: to make provider a mandatory param.
# maybe it might be better of getting this param from db or appliance w/o making it mandatory.


class Datastore(Pretty, Navigatable):
    """ Model of an infrastructure datastore in cfme

    Args:
        name: Name of the datastore.
        provider_key: Name of the provider this datastore is attached to.

    Note:
        If given a provider_key, it will navigate through ``Infrastructure/Providers`` instead
        of the direct path through ``Infrastructure/Datastores``.
    """
    pretty_attrs = ['name', 'provider_key']

    def __init__(self, name=None, provider_key=None, type=None, appliance=None):
        Navigatable.__init__(self, appliance)
        self.name = name
        self.type = type
        self.quad_name = 'datastore'
        if provider_key:
            self.provider = get_crud(provider_key, appliance=appliance)
        else:
            self.provider = None

    def delete(self, cancel=True):
        """
        Deletes a datastore from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True

        Note:
            Datastore must have 0 hosts and 0 VMs for this to work.
        """
        self.load_details()
        cfg_btn('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def wait_for_delete(self):
        wait_for(lambda: not self.exists, fail_condition=False,
             message="Wait datastore to disappear", num_sec=500, fail_func=sel.refresh)

    def wait_for_appear(self):
        wait_for(lambda: self.exists, fail_condition=False,
             message="Wait datastore to appear", num_sec=1000, fail_func=sel.refresh)

    def load_details(self):
        # todo: to remove this context related functionality along with making provider
        # param mandatory
        if not self.provider:
            navigate_to(self, 'Details')
        else:
            navigate_to(self, 'DetailsFromProvider')

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific datastore.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        self.load_details()
        return details_page.infoblock.text(*ident)

    def get_hosts(self):
        """ Returns names of hosts (from quadicons) that use this datastore

        Returns: List of strings with names or `[]` if no hosts found.
        """
        self.load_details()
        try:
            sel.click(details_page.infoblock.element("Relationships", "Hosts"))
        except sel.NoSuchElementException:
            sel.click(InfoBlock('Relationships', 'Hosts'))
        return [q.name for q in Quadicon.all("host")]

    def get_vms(self):
        """ Returns names of VMs (from quadicons) that use this datastore

        Returns: List of strings with names or `[]` if no vms found.
        """
        self.load_details()
        try:
            list_acc.select('Relationships', "VMs", by_title=False, partial=True)
        except (sel.NoSuchElementException, ListAccordionLinkNotFound):
            sel.click(InfoBlock('Relationships', 'Managed VMs'))
        return [q.name for q in Quadicon.all("vm")]

    def delete_all_attached_vms(self):
        self.load_details()
        sel.click(details_page.infoblock.element("Relationships", "Managed VMs"))
        for q in Quadicon.all('vm'):
            fill(q.checkbox(), True)
        cfg_btn("Remove selected items from the VMDB", invokes_alert=True)
        sel.handle_alert(cancel=False)

    def delete_all_attached_hosts(self):
        self.load_details()
        sel.click(details_page.infoblock.element("Relationships", "Hosts"))
        for q in Quadicon.all('host'):
            fill(q.checkbox(), True)
        path = version.pick({
            version.LOWEST: "Remove Hosts from the VMDB",
            "5.4": "Remove items from the VMDB"})
        cfg_btn(path, invokes_alert=True)
        sel.handle_alert(cancel=False)

    def wait_for_delete_all(self):
        try:
            sel.refresh()
            if sel.is_displayed_text("No Records Found"):
                return True
        except CandidateNotFound:
                return False

    @property
    def exists(self):
        try:
            self.load_details()
            quad = Quadicon(self.name, 'datastore')
            if sel.is_displayed(quad):
                return True
        except sel.NoSuchElementException:
            return False

    def run_smartstate_analysis(self):
        """ Runs smartstate analysis on this host

        Note:
            The host must have valid credentials already set up for this to work.
        """
        self.load_details()
        tb.select('Configuration', 'Perform SmartState Analysis', invokes_alert=True)
        sel.handle_alert()
        flash.assert_message_contain('"{}": scan successfully initiated'.format(self.name))


@navigator.register(Datastore, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Datastores')

    def resetter(self):
        # Reset view and selection
        if version.current_version() >= '5.7':
            accordion.tree('Datastores', 'All Datastores')
        else:
            # todo: there is unsupported accordion in 5.6.3.3. currently it isn't necessary
            # for existing tests
            pass
        tb.select("Grid View")
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(Datastore, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))

    def am_i_here(self):
        return match_page(summary='{} "{}"'.format("Datastore", self.obj.name))


@navigator.register(Datastore, 'DetailsFromProvider')
class DetailsFromProvider(CFMENavigateStep):
    def step(self):
        navigate_to(self.obj.provider, 'Details')
        list_acc.select('Relationships', 'Datastores', by_title=False, partial=True)
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))

    def am_i_here(self):
        return match_page(summary='{} "{}"'.format("Datastore", self.obj.name))


def get_all_datastores(do_not_navigate=False):
    """Returns names (from quadicons) of all datastores"""
    if not do_not_navigate:
        navigate_to(Datastore, 'All')
    return [q.name for q in Quadicon.all("datastore")]
