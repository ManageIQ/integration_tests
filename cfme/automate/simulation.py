# -*- coding: utf-8 -*-
from collections import Mapping

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Form, Input, Select, ShowingInputs, fill, flash, form_buttons


class AVPForm(object):
    """Maps dictionary to Attribute/Value pair subform"""
    # TODO: To be moved to web_ui to be shared with control explorer
    def __init__(self, attr_prefix="attribute_", val_prefix="value_", start_number=1, end_number=5):
        self.ap = attr_prefix
        self.vp = val_prefix
        self.start = start_number
        self.end = end_number

    @property
    def num_fields(self):
        return (self.end - self.start) + 1

    def fill(self, data):
        assert len(data.keys()) <= self.num_fields,\
            "You can fill max. {} fields!".format(self.num_fields)
        for i, key in enumerate(data, self.start):
            fill("input#{}{}".format(self.ap, i), key)
            fill("input#{}{}".format(self.vp, i), data[key])


@fill.method((AVPForm, Mapping))
def _fill_avp_form(avp, data):
    avp.fill(data)


sim_form = Form(fields=[
    ("instance", Select("select#instance_name")),
    ("message", Input("object_message")),
    ("request", Input("object_request")),
    ("attribute", ShowingInputs(
        Select("select#target_class"),
        Select("select#target_id"),
        min_values=1,
    )),
    ("execute_methods", Input("readonly")),
    ("avp", AVPForm()),
])

sim_btn = form_buttons.FormButton("Submit Automation Simulation with the specified options")


def simulate(**data):
    """Runs the simulation of specified Automate object.

    Args:
        **data: See :py:data:`sim_form` for keyword reference
    """
    sel.force_navigate("automate_simulation")
    if data.get("attribute", None) is None:
        t = sel.text(sim_form.attribute[0].options[0]).encode("utf-8")  # None
        sel.select(sim_form.attribute[0], t)
    fill(sim_form, data, action=sim_btn)
    flash.assert_message_match("Automation Simulation has been run")
    flash.assert_no_errors()
