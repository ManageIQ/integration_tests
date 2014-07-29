""" A model of an Infrastructure Datastore in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Datastores pages.
"""

import ui_navigate as nav
# needed before grafting
import cfme.web_ui.menu  # noqa

from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import provider
from cfme.web_ui import Quadicon, Region, listaccordion as list_acc, paginator, toolbar as tb
from functools import partial
from utils.pretty import Pretty

details_page = Region(infoblock_type='detail')

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')


def nav_to_datastore_through_provider(context):
    sel.force_navigate('infrastructure_provider', context=context)
    list_acc.select('Relationships', 'Show all managed Datastores')
    sel.click(Quadicon(context['datastore'].name, 'datastore'))


nav.add_branch(
    'infrastructure_datastores', {
        'infrastructure_datastore':
        lambda ctx: sel.click(Quadicon(ctx['datastore'].name, 'datastore'))
        if 'provider' not in ctx else nav_to_datastore_through_provider(ctx)
    }
)


class Datastore(Pretty):
    """ Model of an infrastructure datastore in cfme

    Args:
        name: Name of the datastore.
        provider_key: Name of the provider this datastore is attached to.

    Note:
        If given a provider_key, it will navigate through ``Infrastructure/Providers`` instead
        of the direct path through ``Infrastructure/Datastores``.
    """
    pretty_attrs = ['name', 'provider_key']

    def __init__(self, name=None, provider_key=None):
        self.name = name
        if provider_key:
            self.provider = provider.get_from_config(provider_key)
        else:
            self.provider = None

    def _get_context(self):
        context = {'datastore': self}
        if self.provider:
            context['provider'] = self.provider
        return context

    def delete(self, cancel=True):
        """
        Deletes a datastore from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True

        Note:
            Datastore must have 0 hosts and 0 VMs for this to work.
        """
        sel.force_navigate('infrastructure_datastore', context=self._get_context())
        cfg_btn('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific datastore.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        if not self._on_detail_page():
            sel.force_navigate('infrastructure_datastore', context=self._get_context())
        return details_page.infoblock.text(*ident)

    def _on_detail_page(self):
        """ Returns ``True`` if on the datastore detail page, ``False`` if not."""
        return sel.is_displayed(
            '//div[@class="dhtmlxInfoBarLabel-2"][contains(., "%s") and contains(., "%s")]'
            % (self.name, "Summary")
        )

    def get_hosts(self):
        """ Gets quadicons of hosts that use this datastore

        Returns: List of :py:class:`cfme.web_ui.Quadicon` objects or `[]` if no hosts found.
        """
        quad_title_locator = ".//div[@id='quadicon']/../../../tr[2]//a"
        quads_root_locator = "//table[@id='content']//td[@id='maincol']"
        if not self._on_hosts_page():
            sel.force_navigate('infrastructure_datastore', context=self._get_context())
            try:
                list_acc.select('Relationships', 'Show all registered Hosts')
            except sel.NoSuchElementException:
                return []

        all_host_quads = []
        for page in paginator.pages():
            quads_root = sel.element(quads_root_locator)
            for quad_title in sel.elements(quad_title_locator, root=quads_root):
                all_host_quads.append(Quadicon(quad_title.get_attribute('title'), 'host'))
        return all_host_quads

    def _on_hosts_page(self):
        """ Returns ``True`` if on the datastore hosts page, ``False`` if not."""
        return sel.is_displayed(
            '//div[@class="dhtmlxInfoBarLabel-2"][contains(., "%s") and contains(., "%s")]'
            % (self.name, "All Registered Hosts")
        )

    @property
    def exists(self):
        try:
            sel.force_navigate('infrastructure_datastore', context=self._get_context())
            return True
        except sel.NoSuchElementException, e:
            if Quadicon(self.name, 'datastore').locate() in e.msg:
                return False
            raise


def get_all_datastores(do_not_navigate=False):
    """Returns list of all datastores"""
    if not do_not_navigate:
        sel.force_navigate('infrastructure_datastores')
    datastores = set([])
    for page in paginator.pages():
        for title in sel.elements(
                "//div[@id='quadicon']/../../../tr/td/a[contains(@href,'storage/show')]"):
            datastores.add(sel.get_attribute(title, "title"))
    return datastores
