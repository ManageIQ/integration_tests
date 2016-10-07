""" A model of an Infrastructure Resource pool in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Resource pool pages.
"""
from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Quadicon, Region, toolbar as tb, paginator, summary_title
from functools import partial
from utils.pretty import Pretty
from utils.providers import get_crud
from utils.wait import wait_for
from utils.appliance import Navigatable
from utils.appliance.endpoints.ui import navigator, CFMENavigateStep, navigate_to


details_page = Region(infoblock_type='detail')

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')


class ResourcePool(Pretty, Navigatable):
    """ Model of an infrastructure Resource pool in cfme

    Args:
        name: Name of the Resource pool.
        provider_key: Name of the provider this resource pool is attached to.

    Note:
        If given a provider_key, it will navigate through ``Infrastructure/Providers`` instead
        of the direct path through ``Infrastructure/Resourcepool``.
    """
    pretty_attrs = ['name', 'provider_key']

    def __init__(self, name=None, provider_key=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.quad_name = 'resource_pool'
        self.name = name
        if provider_key:
            self.provider = get_crud(provider_key)
        else:
            self.provider = None

    def _get_context(self):
        context = {'resource_pool': self}
        if self.provider:
            context['provider'] = self.provider
        return context

    def delete(self, cancel=True):
        """Deletes a resource pool from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """
        navigate_to(self, 'Details')
        cfg_btn('Remove from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def wait_for_delete(self):
        navigate_to(self, 'All')
        wait_for(lambda: not self.exists, fail_condition=False,
                 message="Wait resource pool to disappear", num_sec=500, fail_func=sel.refresh)

    def wait_for_appear(self):
        navigate_to(self, 'All')
        wait_for(lambda: self.exists, fail_condition=False,
                 message="Wait resource pool to appear", num_sec=1000, fail_func=sel.refresh)

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific resource pool.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        navigate_to(self, 'Details')
        return details_page.infoblock.text(*ident)

    @property
    def exists(self):
        try:
            navigate_to(self, 'All')
            quad = Quadicon(self.name, self.quad_name)
            if sel.is_displayed(quad):
                return True
        except sel.NoSuchElementException:
            return False


@navigator.register(ResourcePool, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Infrastructure', 'Resource Pools')(None)

    def resetter(self):
        # Reset view and selection
        tb.select("Grid View")
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(ResourcePool, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))

    def am_i_here(self):
        return summary_title() == "{} (Summary)".format(self.obj.name)


def get_all_resourcepools(do_not_navigate=False):
    """Returns list of all resource pools"""
    if not do_not_navigate:
        navigate_to(ResourcePool, 'All')
    return [q.name for q in Quadicon.all(qtype='resource_pool')]
