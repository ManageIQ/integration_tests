from navmazing import NavigateToSibling, NavigateToAttribute

from . import PXEServer
from utils.appliance import ViaUI

from cfme.exceptions import CandidateNotFound
from selenium.common.exceptions import NoSuchElementException
from functools import partial
import cfme.web_ui.toolbar as tb
import cfme.web_ui.accordion as acc
from utils.appliance.endpoints.ui import navigator, CFMENavigateStep, navigate_to

cfg_btn = partial(tb.select, 'Configuration')

pxe_tree = partial(acc.tree, "PXE Servers", "All PXE Servers")


@PXEServer.exists.external_implementation_for(ViaUI)
def exists_ux(self):
    """
    Checks if the PXE server already exists
    """
    # ** Here we are talking to the Sentaku system and asking for the implementation object,
    # ** or the endpoint object. This object is what enables us to "talk" to the endpoint, so
    # ** in this example it provides force_navigate, a browser, and other UI related things.
    # ** Over in the db module it will provide a db session.

    # ** Notice also how the rest of the UI stuff, like pxe_tree remains unchanged. This is our
    # ** desire, to leave as much of the objects code intact as possible.
    navigate_to(self, 'All')
    try:
        pxe_tree(self.name)
        return True
    except CandidateNotFound:
        return False
    except NoSuchElementException:
        return False


@navigator.register(PXEServer, 'All')
class PXEServerAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Infrastructure', 'PXE')(None)
        acc.tree("PXE Servers", "All PXE Servers")


@navigator.register(PXEServer, 'Add')
class PXEServerAdd(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn('Add a New PXE Server')


@navigator.register(PXEServer, 'Details')
class PXEServerDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        acc.tree("PXE Servers", "All PXE Servers", self.obj.name)


@navigator.register(PXEServer, 'Edit')
class PXEServerEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn('Edit this PXE Server')
