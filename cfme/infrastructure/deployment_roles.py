""" A model of an Infrastructure Deployment roles in CFME"""

from functools import partial
from navmazing import NavigateToAttribute, NavigateToSibling
from selenium.common.exceptions import NoSuchElementException

from cfme.exceptions import DestinationNotFound
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
match_page = partial(match_location, controller='ems_cluster',
                     title='Deployment Roles')


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
        nav_path = ('Compute', 'Infrastructure', 'Deployment Roles')
        try:
            self.prerequisite_view.navigation.select(*nav_path)
        except NoSuchElementException:
            raise DestinationNotFound('Navigation {} not found'.format(nav_path))

    def am_i_here(self):
        return match_page(summary='Deployment Roles')


@navigator.register(DeploymentRoles, 'AllForProvider')
class AllForProvider(CFMENavigateStep):

    def prerequisite(self):
        navigate_to(self.obj.provider, 'Details')

    def step(self):
        list_acc.select('Relationships', 'Show all managed Deployment Roles',
                        by_title=True, partial=False)

    def am_i_here(self):
        summary = "{} (All Deployment Roles)".format(self.obj.provider.name)
        return match_page(summary=summary)


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
