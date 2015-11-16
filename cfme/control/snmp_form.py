#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""This file contains useful classes for working with SNMP filling."""

from collections import Mapping

from cfme.web_ui import Select, Form, fill, Input
from cfme.fixtures import pytest_selenium as sel
from utils.log import logger
from utils.pretty import Pretty


class SNMPTrap(Pretty):
    """Nicer representation of the single SNMP trap

    Args:
        oid: SNMP OID
        type: SNMP type
        value: Value (default: `None`)
    """
    pretty_attrs = ['oid', 'type', 'value']

    def __init__(self, oid, type, value=None):
        self.oid = oid
        self.type = type
        self.value = value

    @property
    def as_tuple(self):
        """Return the contents as a tuple used for filling"""
        return (self.oid, self.type, self.value)


class SNMPTrapField(Pretty):
    """Class representing SNMP trap field consisting of 3 elements - oid, type and value

    Args:
        seq_id: Sequential id of the field. Usually in range 1-10
    """
    pretty_attrs = ['seq_id']

    def __init__(self, seq_id):
        self.seq_id = seq_id

    @property
    def oid_loc(self):
        return Input('oid__{}'.format(self.seq_id))

    @property
    def oid(self):
        return sel.get_attribute(self.oid_loc, "value")

    @oid.setter
    def oid(self, value):
        return fill(self.oid_loc, value)

    @property
    def type_loc(self):
        return Select("//select[@id='var_type__%d']" % self.seq_id)

    @property
    def type(self):
        return sel.text(sel.type_loc.first_selected_option)

    @type.setter
    def type(self, value):
        return fill(self.type_loc, value)

    @property
    def value_loc(self):
        return Input('value__{}'.format(self.seq_id))

    @property
    def value(self):
        return sel.get_attribute(self.value_loc, "value")

    @value.setter
    def value(self, value):
        return fill(self.value_loc, value)


@fill.method((SNMPTrapField, SNMPTrap))
def fill_snmp_trap_field_trap(field, val):
    return fill(field, val.as_tuple)


@fill.method((SNMPTrapField, tuple))
def fill_snmp_trap_field_tuple(field, val):
    assert 2 <= len(val) <= 3, "The tuple must be at least 2 items and max 3 items!"
    if len(val) == 2:
        val = val + (None,)
    logger.debug(' Filling in SNMPTrapField #%d with values %s, %s, %s' % ((field.seq_id,) + val))
    field.oid, field.type, field.value = val


@fill.method((SNMPTrapField, Mapping))  # dict because we disassemble it in web_ui
def fill_snmp_trap_field_dict(field, val):
    return fill(field, (val["oid"], val["type"], val.get("value", None)))


class SNMPTrapsField(Pretty):
    """Encapsulates all trap fields to simplify form filling

    Args:
        num_fields: How many SNMPTrapField to generate
    """
    pretty_attrs = ['num_fields']

    def __init__(self, num_fields):
        assert num_fields > 0, "You must have at least one field!"
        self.traps = [SNMPTrapField(i + 1) for i in range(num_fields)]


@fill.method((SNMPTrapsField, list))
def fill_snmp_traps_field_list(field, values):
    assert len(values) <= len(field.traps), "You cannot specify more traps than fields"
    for i, value in enumerate(values):
        fill(field.traps[i], value)


@fill.method((SNMPTrapsField, SNMPTrap))
@fill.method((SNMPTrapsField, tuple))
def fill_snmp_traps_field_single_trap(field, value):
    fill(field.traps[0], value)


class SNMPHostsField(object):
    """Class designed for handling the two-type snmp hosts field.

    They can be 3 or just single."""
    @property
    def host_fields(self):
        """Returns list of locators to all host fields"""
        if sel.is_displayed(Input('host')):
            return [Input('host')]
        else:
            return [Input('host_{}'.format(i + 1)) for i in range(3)]


@fill.method((SNMPHostsField, list))
@fill.method((SNMPHostsField, tuple))
def fill_snmp_hosts_field_list(field, values):
    fields = field.host_fields
    if len(values) > len(fields):
        raise ValueError("You cannot specify more hosts than the form allows!")
    for i, value in enumerate(values):
        fill(fields[i], value)


@fill.method((SNMPHostsField, basestring))
def fill_snmp_hosts_field_basestr(field, value):
    fill(field, [value])


class SNMPForm(object):
    """Class encapsulating the most common (and hopefully single) configuration of SNMP form

    Usage:

        form = SNMPForm()
        fill(form, dict(
            hosts=["host1", "host2"],
            traps=[
                ("aaa", "Counter32", 125),                      # Takes 3-tuples
                ("bbb", "Null"),                                # 2-tuples with no value specified
                SNMPTrap("ccc", "Gauge32", 256),                # objects dtto
                SNMPTrap("ddd", "Null"),                        # value can be unspecified too
                {"oid": "eee", "type": "Integer", "value": 42}  # omg dict too! Yay.
            ],
            version="v2",
            id="aabcd",
        ))

    """
    fields = Form(fields=[
        ("hosts", SNMPHostsField()),
        ("version", Select("//select[@id='snmp_version']")),
        ("id", Input('trap_id')),
        ("traps", SNMPTrapsField(10)),
    ])


@fill.method((SNMPForm, dict))
def fill_snmp_form(form, values, action):
    """I wanted to use dict but that is overrided in web_ui that it disassembles dict to list
    of tuples :("""
    return fill(form.fields, values)
