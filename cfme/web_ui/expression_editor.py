# -*- coding: utf-8 -*-
""" The expression editor present in some locations of CFME.

"""
from functools import partial
from selenium.common.exceptions import NoSuchElementException
from multimethods import singledispatch
from utils.wait import wait_for, TimedOutError
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Anything, Calendar, Form, Input, Region, AngularSelect, fill
import re
import sys
import types
from utils.pretty import Pretty


def _make_button(title):
    return "//span[not(contains(@style,'none'))]//img[@alt='{}']".format(title)


def _root():
    return sel.element("//div[@id='exp_editor_div']")


def _atom_root():
    return sel.element("./div[@id='exp_atom_editor_div']", root=_root())


def _expressions_root():
    return sel.element("./fieldset/div", root=_root())


###
# Buttons container
buttons = Region(
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
            "//a[contains(@id,'exp_')][contains(normalize-space(text()),'{}')]".format(text),
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
            "//a[contains(@id,'exp_')][contains(normalize-space(text()),'???')]",
            root=_expressions_root()
        )
        return True
    except NoSuchElementException:
        return False


def delete_whole_expression():
    while any_expression_present():
        select_first_expression()
        click_remove()


def get_expression_as_text():
    """ Returns whole expression as represented visually.

    """
    return sel.text("//div[@id='exp_editor_div']/fieldset/div").encode("utf-8").strip()


###
# Form handling
#
field_form = Form(
    fields=[
        ("type", AngularSelect("chosen_typ")),
        ("field", AngularSelect("chosen_field")),
        ("key", AngularSelect("chosen_key")),
        ("value", Input("chosen_value")),
        ("user_input", Input("user_input")),
    ]
)

field_date_form = Form(
    fields=[
        ("dropdown_select", AngularSelect("chosen_from_1")),
        ("input_select_date", Calendar("miq_date_1_0")),
        ("input_select_time", AngularSelect("miq_time_1_0"))
    ]
)

count_form = Form(
    fields=[
        ("type", AngularSelect("chosen_typ")),
        ("count", AngularSelect("chosen_count")),
        ("key", AngularSelect("chosen_key", exact=True)),
        ("value", Input("chosen_value")),
        ("user_input", Input("user_input")),
    ]
)

tag_form = Form(
    fields=[
        ("type", AngularSelect("chosen_typ")),
        ("tag", AngularSelect("chosen_tag")),
        ("value", AngularSelect("chosen_value")),
        ("user_input", Input("user_input")),
    ]
)

find_form = Form(
    fields=[
        ("type", AngularSelect("chosen_typ")),
        ("field", AngularSelect("chosen_field")),
        ("skey", AngularSelect("chosen_skey")),
        ("value", "#chosen_value"),
        ("check", AngularSelect("chosen_check")),
        ("cfield", AngularSelect("chosen_cfield", exact=True)),
        ("ckey", AngularSelect("chosen_ckey")),
        ("cvalue", Input("chosen_cvalue")),
    ]
)

registry_form = Form(
    fields=[
        ("type", AngularSelect("chosen_typ")),
        ("key", Input("chosen_regkey")),
        ("value", Input("chosen_regval")),
        ("operation", AngularSelect("chosen_key")),
        ("contents", Input("chosen_value")),
    ]
)

date_switch_buttons = Region(
    locators=dict(
        to_relative="//img[@alt='Click to change to a relative Date/Time format']",
        to_specific="//img[@alt='Click to change to a specific Date/Time format']"
    )
)

date_specific_form = Form(
    fields=[
        ("date", Calendar("miq_date_1_0")),
        ("time", AngularSelect("miq_time_1_0")),
    ]
)

date_relative_form = Form(
    fields=[
        ("from", AngularSelect("chosen_from_1")),
        ("through", AngularSelect("chosen_through_1")),
    ]
)


###
# Fill commands
#
def fill_count(count=None, key=None, value=None):
    """ Fills the 'Count of' type of form.

    If the value is unspecified and we are in the advanced search form (user input), the user_input
    checkbox will be checked if the value is None.

    Args:
        count: Name of the field to compare (Host.VMs, ...).
        key: Operation to do (=, <, >=, ...).
        value: Value to check against.
    Returns: See :py:func:`cfme.web_ui.fill`.
    """
    fill(
        count_form,
        dict(
            type="Count of",
            count=count,
            key=key,
            value=value,
        ),
    )
    # In case of advanced search box
    if sel.is_displayed(field_form.user_input):
        user_input = value is None
    else:
        user_input = None
    fill(field_form.user_input, user_input)
    sel.click(buttons.commit)


def fill_tag(tag=None, value=None):
    """ Fills the 'Tag' type of form.

    Args:
        tag: Name of the field to compare.
        value: Value to check against.
    Returns: See :py:func:`cfme.web_ui.fill`.
    """
    fill(
        tag_form,
        dict(
            type="Tag",
            tag=tag,
            value=value,
        ),
    )
    # In case of advanced search box
    if sel.is_displayed(field_form.user_input):
        user_input = value is None
    else:
        user_input = None
    fill(field_form.user_input, user_input)
    sel.click(buttons.commit)


def fill_registry(key=None, value=None, operation=None, contents=None):
    """ Fills the 'Registry' type of form."""
    return fill(
        registry_form,
        dict(
            type="Registry",
            key=key,
            value=value,
            operation=operation,
            contents=contents,
        ),
        action=buttons.commit
    )


def fill_find(field=None, skey=None, value=None, check=None, cfield=None, ckey=None, cvalue=None):
    fill(
        find_form,
        dict(
            type="Find",
            field=field,
            skey=skey,
            value=value,
            check=check,
            cfield=cfield,
            ckey=ckey,
            cvalue=cvalue,))
    sel.click(buttons.commit)


def fill_field(field=None, key=None, value=None):
    """ Fills the 'Field' type of form.

    Args:
        tag: Name of the field to compare (Host.VMs, ...).
        key: Operation to do (=, <, >=, IS NULL, ...).
        value: Value to check against.
    Returns: See :py:func:`cfme.web_ui.fill`.
    """
    field_norm = field.strip().lower()
    if "date updated" in field_norm or "date created" in field_norm or "boot time" in field_norm:
        no_date = False
    else:
        no_date = True
    fill(
        field_form,
        dict(
            type="Field",
            field=field,
            key=key,
            value=value if no_date else None,
        ),
    )
    # In case of advanced search box
    if sel.is_displayed(field_form.user_input):
        user_input = value is None
    else:
        user_input = None
    fill(field_form.user_input, user_input)
    if not no_date:
        # Flip the right part of form
        if isinstance(value, basestring) and not re.match(r"^[0-9]{2}/[0-9]{2}/[0-9]{4}$", value):
            if not sel.is_displayed(field_date_form.dropdown_select):
                sel.click(date_switch_buttons.to_relative)
            fill(field_date_form, {"dropdown_select": value})
            sel.click(buttons.commit)
        else:
            # Specific selection
            if not sel.is_displayed(field_date_form.input_select_date):
                sel.click(date_switch_buttons.to_specific)
            if (isinstance(value, tuple) or isinstance(value, list)) and len(value) == 2:
                date, time = value
            elif isinstance(value, basestring):  # is in correct format mm/dd/yyyy
                # Date only (for now)
                date = value[:]
                time = None
            else:
                raise TypeError("fill_field expects a 2-tuple (date, time) or string with date")
            # TODO datetime.datetime support
            fill(field_date_form.input_select_date, date)
            # Try waiting a little bit for time field
            # If we don't wait, committing the expression will glitch
            try:
                wait_for(lambda: sel.is_displayed(field_date_form.input_select_time), num_sec=6)
                # It appeared, so if the time is to be set, we will set it (passing None glitches)
                if time:
                    fill(field_date_form.input_select_time, time)
            except TimedOutError:
                # Did not appear, ignore that
                pass
            finally:
                # And finally, commit the expression :)
                sel.click(buttons.commit)
    else:
        sel.click(buttons.commit)


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
    assert name not in _banned_commands, "Command '{}' is not permitted!".format(name)
    assert not name.startswith("_"), "Command '{}' is private!".format(name)
    try:
        func = getattr(sys.modules[__name__], name)
    except AttributeError:
        raise NameError("Could not find function {} to operate the editor!".format(name))
    try:
        func.__call__
        return func
    except AttributeError:
        raise NameError("{} is not callable!".format(name))


def run_commands(command_list, clear_expression=True):
    """ Run commands from the command list.

    Command list syntax:
        .. code-block:: python

            [
                "function1",                                                # no args
                "function2",                                                # dtto
                {"fill_fields": {"field1": "value", "field2": "value"}},    # Passes kwargs
                {"do_other_things": [1,2,3]}                                # Passes args
            ]

    In YAML:
        .. code-block:: yaml

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
                    raise Exception("I use '{}' type here!".format(type(value).__name__))
                step_list.append(partial(func, *args, **kwargs))
        else:
            raise Exception("I cannot process '{}' type here!".format(type(command).__name__))
    if clear_expression:
        delete_whole_expression()
    for step in step_list:
        step()


@singledispatch
def create_program(source):
    """ Wrong call

    """
    raise TypeError("Program code wrong! You must specify string (DSL), command list or None!")


@create_program.method(basestring)
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
            raise SyntaxError("Could not resolve statement `{}' on line {}".format(line, i))
        fname = args_match.groupdict()["name"]
        args = [x.strip() for x in args_match.groupdict()["args"].split(",")]
        if len(args) > 0 and len(args[0]) > 0:
            if re.match(KWARG, args[0]):
                # kwargs
                kwargs = dict([map(lambda x: x.strip(), x.split("=", 1)) for x in args])
                command_list.append({fname: kwargs})
            else:
                # Args
                command_list.append({fname: [None if arg == "/None/" else arg for arg in args]})
        else:
            command_list.append(fname)
    return create_program(command_list)


@create_program.method(list)
@create_program.method(tuple)
def _create_program_from_list(command_list):
    """ Create function which fills the expression from the command list.

    Args:
        command_list: Command list for :py:func:`run_program`
    Returns: Callable, which fills the expression.
    """
    return partial(run_commands, command_list)


@create_program.method(types.NoneType)
def _create_program_from_none(none):
    return lambda: none


class Expression(Pretty):
    """This class enables to embed the expression in a Form.

    Args:
        show_func: Function to call to show the expression if there are more of them.
    """
    pretty_attrs = ['show_func']

    def __init__(self, show_func=lambda: None):
        self.show_func = show_func


@fill.method((Expression, Anything))
def _fill_expression(e, p):
    e.show_func()
    prog = create_program(p)
    prog()
