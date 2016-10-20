# -*- coding: utf-8 -*-
import cfme.fixtures.pytest_selenium as sel
from navmazing import NavigateToAttribute
from cfme.common import SummaryMixin, Taggable
from utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from utils.appliance import Navigatable
from cfme.web_ui import (Quadicon, flash, Form, Input, form_buttons, fill, AngularSelect,
     CheckboxTable)
from functools import partial
from cfme.web_ui import toolbar as tb
from utils.wait import wait_for


cfg_btn = partial(tb.select, "Configuration")
keypair_form = Form(
    fields=[
        ('name', Input("name")),
        ('public_key', Input("public_key")),
        ('provider', AngularSelect('ems_id')),
        ('save_button', form_buttons.add)
    ])

keypair_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")


class KeyPair(Taggable, SummaryMixin, Navigatable):
    """ Automate Model page of KeyPairs

    Args:
        name: Name of Keypairs.
    """

    def __init__(self, name, provider, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.provider = provider

    def delete(self):
        navigate_to(self, 'All')
        keypair_tbl.select_row_by_cells({'Name': self.name})
        cfg_btn('Remove selected Key Pairs', invokes_alert=True)
        sel.handle_alert(cancel=False)
        flash.assert_message_match('Delete initiated for 1 Key Pair')

    def wait_for_delete(self):
        navigate_to(self, 'All')
        quad = Quadicon(self.name, 'keypairs')
        wait_for(lambda: not sel.is_displayed(quad), fail_condition=False,
            message="Wait keypairs to disappear", num_sec=500, fail_func=sel.refresh)

    def create(self, cancel=False):
        """Create new keypair"""
        navigate_to(self, 'All')
        cfg_btn('Add a new Key Pair')
        fill(keypair_form, {'name': self.name, 'provider': self.provider.name},
             action=keypair_form.save_button)
        if not cancel:
            flash.assert_message_match('Creating Key Pair {}'.format(self.name))
        else:
            flash.assert_message_match('Add of new Key Pair was cancelled by the user')


@navigator.register(KeyPair, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Clouds', 'Key Pairs')(None)
