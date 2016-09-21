""" A model of an Infrastructure Cluster in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Cluster pages.
"""
from functools import partial

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Quadicon, Region, listaccordion as list_acc, toolbar as tb, flash
from cfme.web_ui.menu import nav
from utils.api import rest_api
from utils.appliance.endpoints.ui import navigate_to
from utils.pretty import Pretty
from utils.providers import get_crud, get_provider_key
from utils.wait import wait_for

details_page = Region(infoblock_type='detail')

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')


def nav_to_cluster_through_provider(context):
    # TODO: replace this navigation via navmazing and a CFMENavigateStep destination
    navigate_to(context['provider'], 'All')
    list_acc.select('Relationships', 'Clusters', by_title=False, partial=True)
    sel.click(Quadicon(context['cluster'].name, 'cluster'))


nav.add_branch(
    'infrastructure_clusters', {
        'infrastructure_cluster':
            lambda ctx: sel.click(Quadicon(ctx['cluster'].name, 'cluster'))
            if 'provider' not in ctx else nav_to_cluster_through_provider(ctx)
    }
)


class Cluster(Pretty):
    """ Model of an infrastructure cluster in cfme

    Args:
        name: Name of the cluster.
        provider_key: Name of the provider this cluster is attached to.

    Note:
        If given a provider_key, it will navigate through ``Infrastructure/Providers`` instead
        of the direct path through ``Infrastructure/Clusters``.
    """
    pretty_attrs = ['name', 'provider_key']

    def __init__(self, name=None, provider_key=None):
        self.name = name
        self._short_name = self.name.split('in')[0].strip()

        col = rest_api().collections
        cluster = [cl for cl in col.clusters.all if cl.name == self._short_name][-1]
        self._cluster_id = cluster.id
        provider_id = cluster.ems_id

        #  fixme: to remove this part when provider_key becomes mandatory field
        if not provider_key:
            provider_name = [pr.name for pr in col.providers.all if pr.id == provider_id][-1]
            provider_key = get_provider_key(provider_name)

        self.provider = get_crud(provider_key)

    def _get_context(self):
        context = {'cluster': self}
        if self.provider:
            context['provider'] = self.provider
        return context

    def delete(self, cancel=True):
        """
        Deletes a cluster from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """
        sel.force_navigate('infrastructure_cluster', context=self._get_context())
        cfg_btn('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def wait_for_delete(self):
        sel.force_navigate('infrastructure_clusters')
        wait_for(lambda: not self.exists, fail_condition=False,
                 message="Wait cluster to disappear", num_sec=500, fail_func=sel.refresh)

    def wait_for_appear(self):
        sel.force_navigate('infrastructure_clusters')
        wait_for(lambda: self.exists, fail_condition=False,
                 message="Wait cluster to appear", num_sec=1000, fail_func=sel.refresh)

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific cluster.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        if not self._on_detail_page():
            sel.force_navigate('infrastructure_cluster', context=self._get_context())
        return details_page.infoblock.text(*ident)

    def _on_detail_page(self):
        """ Returns ``True`` if on the cluster detail page, ``False`` if not."""
        return sel.is_displayed(
            '//div[@class="dhtmlxInfoBarLabel-2"][contains(., "{}") and contains(., "{}")]'.format(
                self.name, "Summary")
        )

    @property
    def exists(self):
        try:
            sel.force_navigate('infrastructure_cluster', context=self._get_context())
            quad = Quadicon(self.name, 'cluster')
            if sel.is_displayed(quad):
                return True
        except sel.NoSuchElementException:
            return False

    @property
    def cluster_id(self):
        """extracts cluster id for this cluster"""
        return self._cluster_id

    @property
    def short_name(self):
        """returns only cluster's name exactly how it is stored in DB (without datacenter part)"""
        return self._short_name

    def run_smartstate_analysis(self):
        sel.force_navigate('infrastructure_cluster', context={'cluster': self})
        tb.select('Configuration', 'Perform SmartState Analysis', invokes_alert=True)
        sel.handle_alert(cancel=False)
        flash.assert_message_contain('Cluster / Deployment Role: scan successfully initiated')


def get_all_clusters():
    """Returns list of all clusters"""

    sel.force_navigate('infrastructure_clusters')
    clusters = []
    for cluster in Quadicon.all(this_page=True):
        clusters.append(Cluster(cluster.name))
    return clusters
