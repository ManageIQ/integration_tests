from functools import partial
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.update import Updateable
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.toolbar as tb
from utils.pretty import Pretty
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.web_ui import (Region, Quadicon, paginator, match_location)

details_page = Region(infoblock_type='detail')

match_page = partial(match_location, controller='cloud_network',
                     title='Cloud Networks')


class NetworkManager(Updateable, Pretty, Navigatable):
    def __init__(self, name=None, quad_name=None, appliance=None, network_manager_type=None,
                 region=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.quad_name = quad_name
        self.region = region
        self.network_manager_type = network_manager_type

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific host.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        navigate_to(self, 'Details')
        return details_page.infoblock.text(*ident)


@navigator.register(NetworkManager, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Networks', 'Providers')(None)

    def resetter(self):
        tb.select("Grid View")
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(NetworkManager, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))

    def am_i_here(self):
        return match_page(summary="{} (Summary)".format(self.obj.name))
