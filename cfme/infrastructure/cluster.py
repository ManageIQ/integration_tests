""" A model of an Infrastructure Cluster in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Cluster pages.
"""
from functools import partial
from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.fixtures import pytest_selenium as sel
from utils.appliance.endpoints.ui import navigate_to, navigator, CFMENavigateStep
from utils.appliance import Navigatable
from cfme.web_ui import Quadicon, Region, listaccordion as list_acc, toolbar as tb, flash, \
    paginator, summary_title
from utils.pretty import Pretty
from utils.wait import wait_for
from utils.api import rest_api


details_page = Region(infoblock_type='detail')

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')

# todo: since Cluster always requires provider, it will use only one way to get to Cluster Detail's
# page. But we need to fix this in the future.


class Cluster(Pretty, Navigatable):
    """ Model of an infrastructure cluster in cfme

    Args:
        name: Name of the cluster.
        provider: provider this cluster is attached to.

    Note:
        If given a provider_key, it will navigate through ``Infrastructure/Providers`` instead
        of the direct path through ``Infrastructure/Clusters``.
    """
    pretty_attrs = ['name', 'provider']

    def __init__(self, name, provider, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self._short_name = self.name.split('in')[0].strip()
        self.provider = provider
        self.quad_name = 'cluster'

        col = rest_api().collections
        self._id = [cl.id for cl in col.clusters.all if cl.name == self._short_name
                    and cl.ems_id == self.provider.id][-1]

    def delete(self, cancel=True):
        """
        Deletes a cluster from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """
        navigate_to(self, 'Details')
        cfg_btn('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def wait_for_delete(self):
        wait_for(lambda: not self.exists, fail_condition=False,
                 message="Wait cluster to disappear", num_sec=500, fail_func=sel.refresh)

    def wait_for_appear(self):
        wait_for(lambda: self.exists, fail_condition=False,
                 message="Wait cluster to appear", num_sec=1000, fail_func=sel.refresh)

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific cluster.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        navigate_to(self, 'Details')
        return details_page.infoblock.text(*ident)

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            quad = Quadicon(self.name, self.quad_name)
            if sel.is_displayed(quad):
                return True
        except sel.NoSuchElementException:
            return False

    @property
    def id(self):
        """extracts cluster id for this cluster"""
        return self._id

    @property
    def short_name(self):
        """returns only cluster's name exactly how it is stored in DB (without datacenter part)"""
        return self._short_name

    def run_smartstate_analysis(self):
        navigate_to(self, 'Details')
        tb.select('Configuration', 'Perform SmartState Analysis', invokes_alert=True)
        sel.handle_alert(cancel=False)
        flash.assert_message_contain('Cluster / Deployment Role: scan successfully initiated')


@navigator.register(Cluster, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Infrastructure', 'Clusters')(None)

    def resetter(self):
        tb.select("Grid View")
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(Cluster, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))

    def am_i_here(self):
        return summary_title() == "{} (Summary)".format(self.obj.name)


@navigator.register(Cluster, 'DetailsFromProvider')
class DetailsFromProvider(CFMENavigateStep):
    def step(self):
        navigate_to(self.obj.provider, 'Details')
        list_acc.select('Relationships', 'Show all managed Clusters', by_title=True, partial=False)
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))

    def am_i_here(self):
        return summary_title() == "{} (Summary)".format(self.obj.name)
