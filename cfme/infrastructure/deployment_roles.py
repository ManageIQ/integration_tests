""" A model of an Infrastructure Deployment roles in CFME"""

from functools import partial
from navmazing import NavigateToAttribute, NavigateToSibling

from cfme.exceptions import DestinationNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import (CFMENavigateStep, navigate_to,
                                                navigator)
from cfme.web_ui import (listaccordion as list_acc, match_location, Quadicon,
                         Region, toolbar as tb)
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
            raise DestinationNotFound('Deployment roles available only '
                                      'for Openstack provider')
        self.name = name
        self.provider = provider


@navigator.register(DeploymentRoles, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure',
                                                 'Deployment Roles')

    def am_i_here(self):
        return match_location(match_page)


@navigator.register(DeploymentRoles, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name))

    def am_i_here(self):
        return match_page(summary="{} (Summary)".format(self.obj.name))


@navigator.register(DeploymentRoles, 'DetailsFromProvider')
class DetailsFromProvider(CFMENavigateStep):
    def step(self):
        navigate_to(self.obj.provider, 'Details')
        list_acc.select('Relationships', 'Show all managed Deployment Roles',
                        by_title=True, partial=False)
        sel.click(Quadicon(self.obj.name))

    def am_i_here(self):
        return match_page(summary="{} (Summary)".format(self.obj.name))
