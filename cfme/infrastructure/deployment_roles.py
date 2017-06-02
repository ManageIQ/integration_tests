""" A model of an Infrastructure Deployment roles in CFME"""

from functools import partial
from navmazing import NavigateToAttribute, NavigateToSibling
from selenium.common.exceptions import NoSuchElementException

from cfme.exceptions import ListAccordionLinkNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import (CFMENavigateStep, navigate_to,
                                                navigator)
from cfme.web_ui import (listaccordion as list_acc, match_location, Quadicon,
                         Region, toolbar as tb)
from utils import version
from utils.pretty import Pretty


details_page = Region(infoblock_type='detail')

cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')
match_page = partial(match_location, controller='ems_cluster')


class DeploymentRoles(Pretty, Navigatable):
    """ Model of an infrastructure deployment roles in cfme

    Args:
        name: Name of the role.
        provider: provider this role is attached to
            (deployment roles available only for Openstack!).
    """
    pretty_attrs = ['name', 'provider']

    def __init__(self, name, provider, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        if not isinstance(provider, OpenstackInfraProvider):
            raise NotImplementedError('Deployment roles available only '
                                      'for Openstack provider')
        self.name = name
        self.provider = provider

    def get_detail(self, *ident):
        """ Gets details from the details InfoBlock
        Args:
            *ident: An InfoBlock title, followed by the Key name,
                e.g. "Relationships", "All VMs"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        navigate_to(self, 'Details')
        return details_page.infoblock.text(*ident)

    def delete(self):
        navigate_to(self, 'Details')
        menu_item = version.pick({version.LOWEST: 'Remove from the VMDB',
                                  '5.7': 'Remove item'})
        cfg_btn(menu_item, invokes_alert=True)
        sel.handle_alert(wait=60)


@navigator.register(DeploymentRoles, 'All')
class All(CFMENavigateStep):

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        nav_select = partial(self.prerequisite_view.navigation.select, 'Compute', 'Infrastructure')
        try:
            nav_select('Deployment Roles')
        except NoSuchElementException:
            nav_select('Clusters / Deployment Roles')

    def am_i_here(self):
        def match(option):
            return match_page(title=option, summary=option)

        return match('Clusters / Deployment Roles') or match('Deployment Roles')


@navigator.register(DeploymentRoles, 'AllForProvider')
class AllForProvider(CFMENavigateStep):

    def prerequisite(self):
        navigate_to(self.obj.provider, 'Details')

    def step(self):
        def list_acc_select(option):
            list_acc.select('Relationships', 'Show all managed {}'.format(option), by_title=True,
                            partial=False)

        try:
            list_acc_select('Deployment Roles')
        except ListAccordionLinkNotFound:
            list_acc_select('Clusters / Deployment Roles')

    def am_i_here(self):
        def match(option):
            summary_ptrn = "{} (All {})"
            return match_page(summary=summary_ptrn.format(self.obj.provider.name, option),
                              title=option)

        return match('Deployment Roles') or match('Clusters / Deployment Roles')


@navigator.register(DeploymentRoles, 'Details')
class Details(CFMENavigateStep):

    prerequisite = NavigateToSibling('All')

    def step(self):
        tb.select('Grid View')
        sel.click(Quadicon(self.obj.name))

    def am_i_here(self):
        return match_page(summary="{} (Summary)".format(self.obj.name))


@navigator.register(DeploymentRoles, 'DetailsFromProvider')
class DetailsFromProvider(CFMENavigateStep):

    prerequisite = NavigateToSibling('AllForProvider')

    def step(self):
        tb.select('Grid View')
        sel.click(Quadicon(self.obj.name))

    def am_i_here(self):
        return match_page(summary="{} (Summary)".format(self.obj.name))
