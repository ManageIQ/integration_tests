from base import PXEBase
from utils.appliance import ViaUI, current_appliance

from cfme.exceptions import CandidateNotFound
from selenium.common.exceptions import NoSuchElementException
from functools import partial
import cfme.web_ui.toolbar as tb
import cfme.web_ui.accordion as acc

cfg_btn = partial(tb.select, 'Configuration')

pxe_tree = partial(acc.tree, "PXE Servers", "All PXE Servers")

# ** Notice this below. It's hacky. Right now this enables "this" object to work and no other.
# ** Why did we do it this way?
# ** Navigation used to be a single object, now, if you look at utils.appliance, it's endpoint
# ** specific. Meaning that each appliance has a set of endpoint objects and each one of those
# ** has a Menu object. See utils.appliance for more on this.
# ** But in order to get this demo to work, we had to graft the tree directly into the menu.
# ** As the test is only using a single appliance this seemed like the best way to do it.
# ** As things progress we will need to find a way to get nav endpoint loading to happen to "ALL"
# ** relevant endpoint objects an once AND, that when new appliance objects are created, and hence
# ** new endpoint objects are created, they get populated with nav end points that have already
# ** been loaded. This part is a little tricky. But we have some good ideas (most notably, making
# ** the menu system entirely deterministic so that it is version agnostic.
current_appliance.browser.menu.add_branch('infrastructure_pxe',
               {'infrastructure_pxe_servers': [lambda _: pxe_tree(),
                {'infrastructure_pxe_server_new': lambda _: cfg_btn('Add a New PXE Server'),
                 'infrastructure_pxe_server': [lambda ctx: pxe_tree(ctx.pxe_server.name),
                                               {'infrastructure_pxe_server_edit':
                                                lambda _: cfg_btn('Edit this PXE Server')}]}],
                })


class PXEServerUI(PXEBase):
    # ** We inherit the PXEBase object here to gain access to the exists attribute. There was no
    # ** other easy way with the current Sentaku implementation without creating a circular
    # **  dependency. At least, there was no way which made sense to me.

    # ** Notice that we only have one method in here right now, that's the exists method. It's
    # ** name is 'existse' on purpose to show that when we use it, the methods ACTUAL name
    # ** doesn't matter. That it is the "exists" in the @PXEBase.exists...... line that denotes
    # ** how it will be called.
    @PXEBase.exists.implemented_for(ViaUI)
    def existse(self):
        """
        Checks if the PXE server already exists
        """
        # ** Here we are talking to the Sentaku system and asking for the implementation object,
        # ** or the endpoint object. This object is what enables us to "talk" to the endpoint, so
        # ** in this example it provides force_navigate, a browser, and other UI related things.
        # ** Over in the db module it will provide a db session.

        # ** Notice also how the rest of the UI stuff, like pxe_tree remains unchanged. This is our
        # ** desire, to leave as much of the objects code intact as possible.
        self.impl.force_navigate('infrastructure_pxe_servers')
        try:
            pxe_tree(self.name)
            return True
        except CandidateNotFound:
            return False
        except NoSuchElementException:
            return False
