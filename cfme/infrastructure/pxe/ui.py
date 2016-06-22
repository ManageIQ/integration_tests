from base import PXEBase
from utils.appliance import ViaUI, current_appliance

from cfme.exceptions import CandidateNotFound
from selenium.common.exceptions import NoSuchElementException
from functools import partial
import cfme.web_ui.toolbar as tb
import cfme.web_ui.accordion as acc

cfg_btn = partial(tb.select, 'Configuration')

pxe_tree = partial(acc.tree, "PXE Servers", "All PXE Servers")

current_appliance.browser.menu.add_branch('infrastructure_pxe',
               {'infrastructure_pxe_servers': [lambda _: pxe_tree(),
                {'infrastructure_pxe_server_new': lambda _: cfg_btn('Add a New PXE Server'),
                 'infrastructure_pxe_server': [lambda ctx: pxe_tree(ctx.pxe_server.name),
                                               {'infrastructure_pxe_server_edit':
                                                lambda _: cfg_btn('Edit this PXE Server')}]}],
                })


class PXEServerUI(PXEBase):
    @PXEBase.exists.implemented_for(ViaUI)
    def existse(self):
        """
        Checks if the PXE server already exists
        """
        self.impl.force_navigate('infrastructure_pxe_servers')
        try:
            pxe_tree(self.name)
            return True
        except CandidateNotFound:
            return False
        except NoSuchElementException:
            return False
