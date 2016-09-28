# -*- coding: utf-8 -*-
import cfme.fixtures.pytest_selenium as sel
from cfme.common import SummaryMixin, Taggable
from cfme.web_ui import (Quadicon, flash, Form, Input, form_buttons, fill, AngularSelect,
     CheckboxTable)
from functools import partial
from cfme.web_ui import toolbar as tb, mixins
from utils.wait import wait_for


cfg_btn = partial(tb.select, "Configuration")
pol_btn = partial(tb.select, 'Policy')
keypair_form = Form(
    fields=[
        ('name', Input("name")),
        ('public_key', Input("public_key")),
        ('provider', AngularSelect('ems_id')),
        ('save_button', form_buttons.add)
    ])

keypair_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")


class KeyPair(Taggable, SummaryMixin):
    """ Automate Model page of KeyPairs

    Args:
        name: Name of Keypairs.
    """

    def __init__(self, name=None):
        self.name = name

    def delete(self):
        """ Delete given keypair """
        sel.force_navigate('clouds_key_pairs', context={'keypairs': self.name})
        keypair_tbl.select_row_by_cells({'Name': self.name})
        cfg_btn('Remove selected Key Pairs', invokes_alert=True)
        sel.handle_alert(cancel=False)
        flash.assert_message_match('Delete initiated for 1 Key Pair')

    def wait_for_delete(self):
        sel.force_navigate("clouds_key_pairs")
        quad = Quadicon(self.name, 'keypairs')
        wait_for(lambda: not sel.is_displayed(quad), fail_condition=False,
            message="Wait keypairs to disappear", num_sec=500, fail_func=sel.refresh)

    def create(self, cancel=False):
        """ Create new keypair """
        sel.force_navigate('clouds_key_pairs', context={'keypairs': self.name})
        cfg_btn('Add a new Key Pair')
        fill(keypair_form, {'name': self.name}, action=keypair_form.save_button)
        if not cancel:
            flash.assert_message_match('Creating Key Pair {}'.format(self.name))
        else:
            flash.assert_message_match('Add of new Key Pair was cancelled by the user')

    def add_tag(self, tag):
        """ Add a tag to keypair """
        sel.force_navigate('clouds_key_pairs', context={'keypairs': self.name})
        keypair_tbl.select_row_by_cells({'Name': self.name})
        pol_btn("Edit Tags")
        mixins.add_tag(tag)

    def remove_tag(self, tag):
        """ Remove a tag from keypair """
        sel.force_navigate('clouds_key_pairs', context={'keypairs': self.name})
        keypair_tbl.select_row_by_cells({'Name': self.name})
        pol_btn("Edit Tags")
        mixins.remove_tag(tag)
