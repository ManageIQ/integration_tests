#!/usr/bin/env python2
# -*- coding: utf-8 -*-
""" The expression editor present in some locations of CFME.

"""
from functools import partial
from selenium.common.exceptions import NoSuchElementException
from singledispatch import singledispatch
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui as web_ui
import re
import sys


def _make_button(title):
    return "//span[not(contains(@style,'none'))]//img[@alt='%s']"\
        % title


def _root():
    return sel.element("//div[@id='exp_editor_div']")


def _atom_root():
    return sel.element("./div[@id='exp_atom_editor_div']", root=_root())


def _expressions_root():
    return sel.element("./fieldset/div[@style='padding:10px']", root=_root())


###
# Buttons container
buttons = web_ui.Region(
    locators=dict(
        commit="//img[@alt='Commit expression element changes']",
        discard="//img[@alt='Discard expression element changes']",
        remove="//span[not(contains(@style, 'none'))]//img[@alt='Remove this expression element']",
        NOT="//span[not(contains(@style, 'none'))]" +
            "//img[@alt='Wrap this expression element with a NOT']",
        OR="//span[not(contains(@style, 'none'))]//img[@alt='OR with a new expression element']",
        AND="//span[not(contains(@style, 'none'))]//img[@alt='AND with a new expression element']",
        redo="//img[@alt='Redo']",
        undo="//img[@alt='Undo']",
        select_specific="//img[@alt='Click to change to a specific Date/Time format']",
        select_relative="//img[@alt='Click to change to a relative Date/Time format']",
    )
)


###
# Buttons for operationg the expression concatenation
#
def click_undo():
    sel.click(buttons.undo)


def click_redo():
    sel.click(buttons.redo)


def click_and():
    sel.click(buttons.AND)


def click_or():
    sel.click(buttons.OR)


def click_not():
    sel.click(buttons.NOT)


def click_remove():
    sel.click(buttons.remove)


###
# Buttons for operating the atomic expressions
#
def click_commit():
    sel.click(buttons.commit)


def click_discard():
    sel.click(buttons.discard)


###
# Functions for operating the selection of the expressions
#
def select_first_expression():
    """ There is always at least one (???), so no checking of bounds.

    """
    sel.click(sel.elements("//a[contains(@id,'exp_')]", root=_expressions_root())[0])


def select_expression_by_text(text):
    sel.click(
        sel.element(
            "//a[contains(@id,'exp_')][contains(text(),'%s')]" % text,
            root=_expressions_root()
        )
    )


def no_expression_present():
    els = sel.elements("//a[contains(@id,'exp_')]", root=_expressions_root())
    if len(els) > 1:
        return False
    return els[0].text.strip() == "???"


def any_expression_present():
    return not no_expression_present()


def is_editing():
    try:
        sel.element(
            "//a[contains(@id,'exp_')][contains(text(),'???')]",
            root=_expressions_root()
        )
        return True
    except NoSuchElementException:
        return False


def delete_whole_expression():
    while any_expression_present():
        select_first_expression()
        click_remove()


###
# Form handling
#
field_form = web_ui.Form(
    fields=[
        ("type", "//select[@id='chosen_typ']"),
        ("field", "//select[@id='chosen_field']"),
        ("key", "//select[@id='chosen_key']"),
        ("value", "//*[@id='chosen_value']"),
    ]
)

field_date_form = web_ui.Form(
    fields=[
        ("dropdown_select", "//select[@id='chosen_from_1']"),
        ("input_select_date", "//input[@id='miq_date_1_0']"),
        ("input_select_time", "//select[@id='miq_time_1_0']")
    ]
)

count_form = web_ui.Form(
    fields=[
        ("type", "//select[@id='chosen_typ']"),
        ("count", "//select[@id='chosen_count']"),
        ("key", "//select[@id='chosen_key']"),
        ("value", "//*[@id='chosen_value']"),
    ]
)

tag_form = web_ui.Form(
    fields=[
        ("type", "//select[@id='chosen_typ']"),
        ("count", "//select[@id='chosen_tag']"),
        ("value", "//*[@id='chosen_value']"),
    ]
)

date_switch_buttons = web_ui.Region(
    locators=dict(
        to_relative="img[@alt='Click to change to a relative Date/Time format']",
        to_specific="img[@alt='Click to change to a specific Date/Time format']"
    )
)

date_specific_form = web_ui.Form(
    fields=[
        ("date", "//input[@id='miq_date_1_0']"),
        ("time", "//input[@id='miq_time_1_0']"),
    ]
)

date_relative_form = web_ui.Form(
    fields=[
        ("from", "//select[@id='chosen_from_1']"),
        ("through", "//select[@id='chosen_through_1']"),
    ]
)


###
# Fill commands
#
def fill_count(count=None, key=None, value=None):
    """ Fills the 'Count of' type of form.

    Args:
        count: Name of the field to compare (Host.VMs, ...).
        key: Operation to do (=, <, >=, ...).
        value: Value to check against.
    Returns: See :py:func:`cfme.web_ui.fill`.
    """
    return web_ui.fill(
        count_form,
        dict(
            type="Count of",
            count=count,
            key=key,
            value=value
        ),
        action=buttons.commit
    )


def fill_tag(tag=None, value=None):
    """ Fills the 'Tag' type of form.

    Args:
        tag: Name of the field to compare.
        value: Value to check against.
    Returns: See :py:func:`cfme.web_ui.fill`.
    """
    return web_ui.fill(
        tag_form,
        dict(
            type="Tag",
            tag=tag,
            value=value
        ),
        action=buttons.commit
    )


def fill_field(field=None, key=None, value=None):
    """ Fills the 'Field' type of form.

    Args:
        tag: Name of the field to compare (Host.VMs, ...).
        key: Operation to do (=, <, >=, IS NULL, ...).
        value: Value to check against.
    Returns: See :py:func:`cfme.web_ui.fill`.
    """
    field_norm = field.strip().lower()
    if "date updated" in field_norm or "date created" in field_norm:
        no_date = None
    else:
        no_date = buttons.commit
    web_ui.fill(
        field_form,
        dict(
            type="Field",
            field=field,
            key=key,
            value=value if no_date else None
        ),
        action=no_date
    )
    if not no_date:
        # Flip the right part of form
        if isinstance(value, basestring) and not re.match(r"^[0-9]{2}/[0-9]{2}/[0-9]{4}$", value):
            if not sel.is_displayed(field_date_form.dropdown_select):
                sel.click(buttons.to_relative)
            web_ui.fill(field_date_form, {"dropdown_select": value}, action=buttons.commit)
        else:
            # Specific selection
            if not sel.is_displayed(field_date_form.input_select_date):
                sel.click(buttons.to_specific)
            if (isinstance(value, tuple) or isinstance(value, list)) and len(value) == 2:
                date, time = value
            elif isinstance(value, basestring):  # is in correct format mm/dd/yyyy
                # Date only (for now)
                date = value[:]
                time = None
            else:
                raise TypeError("fill_field expects a 2-tuple (date, time) or string with date")
            # TODO datetime.datetime support
            web_ui.fill(field_date_form,
                        {
                            "input_select_date": date,
                            "input_select_time": time,
                        },
                        action=buttons.commit)


###
# Processor for YAML commands
#
_banned_commands = {"get_func", "run_commands", "dsl_parse", "create_program_from_dsl"}


def get_func(name):
    """ Return callable from this module by its name.

    Args:
        name: Name of the variable containing the callable.
    Returns: Callable from this module
    """
    assert name not in _banned_commands, "Command '%s' is not permitted!" % name
    assert not name.startswith("_"), "Command '%s' is private!" % name
    try:
        func = getattr(sys.modules[__name__], name)
    except AttributeError:
        raise NameError("Could not find function %s to operate the editor!" % name)
    try:
        func.__call__
        return func
    except AttributeError:
        raise NameError("%s is not callable!" % name)


def run_commands(command_list, clear_expression=True):
    """ Run commands from the command list.

    Command list syntax:
    [
        "function1",                                                # no args
        "function2",                                                # dtto
        {"fill_fields": {"field1": "value", "field2": "value"}},    # Passes kwargs
        {"do_other_things": [1,2,3]}                                # Passes args
    ]

    In YAML:
    - function1
    - function2
    -
        fill_fields:
            field1: value
            field2: value
    -
        do_other_things:
            - 1
            - 2
            - 3

    Args:
        command_list: :py:class:`list` object of the commands
        clear_expression: Whether to clear the expression before entering new one (default `True`)
    """
    assert isinstance(command_list, list) or isinstance(command_list, tuple)
    step_list = []
    for command in command_list:
        if isinstance(command, basestring):
            # Single command, no params
            step_list.append(get_func(command))
        elif isinstance(command, dict):
            for key, value in command.iteritems():
                func = get_func(key)
                args = []
                kwargs = {}
                if isinstance(value, list) or isinstance(value, tuple):
                    args.extend(value)
                elif isinstance(value, dict):
                    kwargs.update(value)
                else:
                    raise Exception("I use '%s' type here!" % type(value).__name__)
                step_list.append(partial(func, *args, **kwargs))
        else:
            raise Exception("I cannot process '%s' type here!" % type(command).__name__)
    if clear_expression:
        delete_whole_expression()
    for step in step_list:
        step()


@singledispatch
def create_program(source):
    """ Wrong call

    """
    raise TypeError("Program code wrong! You must specify string (DSL), command list or None!")


@create_program.register(basestring)
def _create_program_from_dsl(dsl_program):
    """ Simple DSL to fill the expression editor.

    Syntax:
        DSL consists from statements. Statements are separated with newline or ;.
        Each statement is a single function call. Functions are called in this module.
        Function without parameters can be called like this:
        function
        or
        function()

        If the function has some parameters, you have to choose whether they are kwargs or args.
        DSL has no string literals, so if you want to call a function with classic parameters:
        function(parameter one, parameter two, you cannot use comma)
        And with kwargs:
        function(username=John Doe, password=top secret)
        You cannot split the statement to multiple lines as the DSL is regexp-based.

    Args:
        dsl_program: Source string with the program.
    Returns: Callable, which fills the expression.
    """
    SIMPLE_CALL = r"^[a-z_A-Z][a-z_A-Z0-9]*$"
    ARGS_CALL = r"^(?P<name>[a-z_A-Z][a-z_A-Z0-9]*)\((?P<args>.*)\)$"
    KWARG = r"^[^=]+=.*$"
    command_list = []
    for i, line in enumerate([x.strip() for x in re.split(r"\n|;", dsl_program)]):
        if len(line) == 0:
            continue
        elif re.match(SIMPLE_CALL, line):
            command_list.append(line)
            continue
        args_match = re.match(ARGS_CALL, line)
        if not args_match:
            raise SyntaxError("Could not resolve statement `%s' on line %d" % (line, i))
        fname = args_match.groupdict()["name"]
        args = [x.strip() for x in args_match.groupdict()["args"].split(",")]
        if len(args) > 0 and len(args[0]) > 0:
            if re.match(KWARG, args[0]):
                # kwargs
                kwargs = dict([x.split("=", 1) for x in args])
                command_list.append({fname: kwargs})
            else:
                # Args
                command_list.append({fname: args})
        else:
            command_list.append(fname)
    return create_program(command_list)


@create_program.register(list)
@create_program.register(tuple)
def _create_program_from_list(command_list):
    """ Create function which fills the expression from the command list.

    Args:
        command_list: Command list for :py:func:`run_program`
    Returns: Callable, which fills the expression.
    """
    return partial(run_commands, command_list)


@create_program.register(None)
def _create_program_from_none(none):
    return lambda: none
