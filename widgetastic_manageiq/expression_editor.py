# -*- coding: utf-8 -*-
""" The expression editor present in some locations of CFME.

"""
from functools import partial
from selenium.common.exceptions import NoSuchElementException
from cfme.utils.wait import wait_for, TimedOutError
import re
from cfme.utils.pretty import Pretty

from widgetastic_patternfly import Input, BootstrapSelect, Button
from widgetastic.widget import View
from widgetastic_manageiq import Calendar, Checkbox
import six


class ExpressionButton(Button):

    def __locator__(self):
        return (
            './/*[(self::a or self::button or (self::input and '
            '(@type="button" or @type="submit"))) {}]'.format(self.locator_conditions))


class ExpressionEditor(View, Pretty):
    """This class enables to embed the expression in a Form.

    Args:
        show_func: Function to call to show the expression if there are more of them.
    """

    @View.nested
    class field_form_view(View):  # noqa
        type = BootstrapSelect("chosen_typ")
        field = BootstrapSelect("chosen_field")
        key = BootstrapSelect("chosen_key")
        value = Input(name="chosen_value")
        user_input = Checkbox(name="user_input")

    @View.nested
    class field_date_form(View):  # noqa
        dropdown_select = BootstrapSelect("chosen_from_1")
        input_select_date = Calendar(name="miq_date_1_0")
        input_select_time = BootstrapSelect("miq_time_1_0")

    @View.nested
    class count_form_view(View):  # noqa
        type = BootstrapSelect("chosen_typ")
        count = BootstrapSelect("chosen_count")
        key = BootstrapSelect("chosen_key")
        value = Input(name="chosen_value")
        user_input = Checkbox(name="user_input")

    @View.nested
    class tag_form_view(View):  # noqa
        type = BootstrapSelect("chosen_typ")
        tag = BootstrapSelect("chosen_tag")
        value = BootstrapSelect("chosen_value")
        user_input = Checkbox(name="user_input")

    @View.nested
    class find_form_view(View):  # noqa
        type = BootstrapSelect("chosen_typ")
        field = BootstrapSelect("chosen_field")
        skey = BootstrapSelect("chosen_skey")
        value = Input(name="chosen_value")
        check = BootstrapSelect("chosen_check")
        cfield = BootstrapSelect("chosen_cfield")
        ckey = BootstrapSelect("chosen_ckey")
        cvalue = Input(name="chosen_cvalue")

    @View.nested
    class registry_form_view(View):  # noqa
        type = BootstrapSelect("chosen_typ")
        key = Input(name="chosen_regkey")
        value = Input(name="chosen_regval")
        operation = BootstrapSelect("chosen_key")
        contents = Input(name="chosen_value")

    @View.nested
    class date_specific_form_view(View):  # noqa
        date = Calendar(name="miq_date_1_0")
        time = BootstrapSelect("miq_time_1_0")

    @View.nested
    class date_relative_form_view(View):  # noqa
        from_ = BootstrapSelect("chosen_from_1")
        through = BootstrapSelect("chosen_through_1")

    ROOT = "//div[@id='exp_editor_div']"
    MAKE_BUTTON = "//span[not(contains(@style,'none'))]//img[@alt='{}']"
    ATOM_ROOT = "./div[@id='exp_atom_editor_div']"
    EXPRESSIONS_ROOT = "./fieldset/div"
    COMMIT = Button(title="Commit expression element changes")
    DISCARD = Button(title="Discard expression element changes")
    REMOVE = Button(title="Remove this expression element")
    NOT = ExpressionButton(title="Wrap this expression element with a NOT")
    OR = ExpressionButton(title="OR with a new expression element")
    AND = ExpressionButton(title="AND with a new expression element")
    REDO = Button(title="Redo the last change")
    UNDO = Button(title="Undo the last change")
    SELECT_SPECIFIC = "//img[@alt='Click to change to a specific Date/Time format']"
    SELECT_RELATIVE = "//img[@alt='Click to change to a relative Date/Time format']"

    pretty_attrs = ['show_loc']

    def __init__(self, parent, show_loc=None, logger=None):
        View.__init__(self, parent, logger=logger)
        self.show_loc = show_loc

    def __locator__(self):
        return self.ROOT

    def click_undo(self):
        self.browser.click(self.UNDO)

    def click_redo(self):
        self.browser.click(self.REDO)

    def click_and(self):
        self.browser.click(self.AND)

    def click_or(self):
        self.browser.click(self.OR)

    def click_not(self):
        self.browser.click(self.NOT)

    def click_remove(self):
        self.browser.click(self.REMOVE)

    def click_commit(self):
        self.browser.click(self.COMMIT)

    def click_discard(self):
        self.browser.click(self.DISCARD)

    def click_switch_to_relative(self):
        self.browser.click(self.SELECT_RELATIVE)

    def click_switch_to_specific(self):
        self.browser.click(self.SELECT_SPECIFIC)

    @property
    def _atom_root(self):
        return self.browser.element(self.ATOM_ROOT)

    @property
    def _expressions_root(self):
        return self.browser.element(self.EXPRESSIONS_ROOT)

    @property
    def expression_text(self):
        return self.browser.text("//a[contains(@id,'exp_')]", parent=self._expressions_root)

    def select_first_expression(self):
        """There is always at least one (???), so no checking of bounds."""
        self.browser.elements("//a[contains(@id,'exp_')]", parent=self._expressions_root)[0].click()

    def select_expression_by_text(self, text):
        self.browser.click(
            "//a[contains(@id,'exp_')][contains(normalize-space(text()),'{}')]".format(text)
        )

    def no_expression_present(self):
        els = self.browser.elements("//a[contains(@id,'exp_')]", parent=self._expressions_root)
        if len(els) > 1:
            return False
        return els[0].text.strip() == "???"

    def any_expression_present(self):
        return not self.no_expression_present()

    def is_editing(self):
        try:
            self.browser.element(
                "//a[contains(@id,'exp_')][contains(normalize-space(text()),'???')]",
                parent=self._expressions_root
            )
            return True
        except NoSuchElementException:
            return False

    def delete_whole_expression(self):
        while self.any_expression_present():
            self.select_first_expression()
            self.click_remove()

    def read(self):
        """Returns whole expression as represented visually."""
        return self.expression_text.encode("utf-8").strip()

    def enable_editor(self):
        try:
            el = self.browser.element(self.show_loc)
            wait_for(lambda: el.is_displayed, num_sec=2, delay=0.2)
            el.click()
        except (TimedOutError, NoSuchElementException):
            pass

    def fill(self, expression):
        if self.show_loc is not None:
            self.enable_editor()
        prog = create_program(expression, self)
        before = self.expression_text.encode("utf-8").strip()
        prog()
        after = self.expression_text.encode("utf-8").strip()
        return before != after

    def fill_count(self, count=None, key=None, value=None):
        """ Fills the 'Count of' type of form.

        If the value is unspecified and we are in the advanced search form (user input),
        the user_input checkbox will be checked if the value is None.

        Args:
            count: Name of the field to compare (Host.VMs, ...).
            key: Operation to do (=, <, >=, ...).
            value: Value to check against.
        """
        view = self.count_form_view
        view.fill(dict(
            type="Count of",
            count=count,
            key=key,
            value=value
        ))
        # In case of advanced search box
        if view.user_input.is_displayed:
            user_input = value is None
            view.user_input.fill(user_input)
        self.click_commit()

    def fill_tag(self, tag=None, value=None):
        """ Fills the 'Tag' type of form.

        Args:
            tag: Name of the field to compare.
            value: Value to check against.
        """
        view = self.tag_form_view
        view.fill(dict(
            type="Tag",
            tag=tag,
            value=value
        ))
        # In case of advanced search box
        if view.user_input.is_displayed:
            user_input = value is None
            view.user_input.fill(user_input)
        self.click_commit()

    def fill_registry(self, key=None, value=None, operation=None, contents=None):
        """ Fills the 'Registry' type of form."""
        view = self.registry_form_view
        view.fill(dict(
            type="Registry",
            key=key,
            value=value,
            operation=operation,
            contents=contents,
        ))
        self.click_commit()

    def fill_find(self, field=None, skey=None, value=None, check=None, cfield=None, ckey=None,
                  cvalue=None):
        view = self.find_form_view
        view.fill(dict(
            type="Find",
            field=field,
            skey=skey,
            value=value,
            check=check,
            cfield=cfield,
            ckey=ckey,
            cvalue=cvalue
        ))
        self.click_commit()

    def fill_field(self, field=None, key=None, value=None):
        """ Fills the 'Field' type of form.

        Args:
            tag: Name of the field to compare (Host.VMs, ...).
            key: Operation to do (=, <, >=, IS NULL, ...).
            value: Value to check against.
        """
        field_norm = field.strip().lower()
        if ("date updated" in field_norm or "date created" in field_norm or
                "boot time" in field_norm or "timestamp" in field_norm):
            no_date = False
        else:
            no_date = True
        view = self.field_form_view
        view.fill(dict(
            type="Field",
            field=field,
            key=key,
            value=value if no_date else None,
        ))
        # In case of advanced search box
        if view.user_input.is_displayed:
            user_input = value is None
            view.user_input.fill(user_input)
        if not no_date:
            # Flip the right part of form
            view = self.field_date_form
            if (isinstance(value, six.string_types) and
                    not re.match(r"^[0-9]{2}/[0-9]{2}/[0-9]{4}$", value)):
                if not view.dropdown_select.is_displayed:
                    self.click_switch_to_relative()
                view.fill({"dropdown_select": value})
                self.click_commit()
            else:
                # Specific selection
                if not view.input_select_date.is_displayed:
                    self.click_switch_to_specific()
                if (isinstance(value, tuple) or isinstance(value, list)) and len(value) == 2:
                    date, time = value
                elif isinstance(value, six.string_types):  # is in correct format mm/dd/yyyy
                    # Date only (for now)
                    date = value[:]
                    time = None
                else:
                    raise TypeError("fill_field expects a 2-tuple (date, time) or string with date")
                # TODO datetime.datetime support
                view.input_select_date.fill(date)
                # Try waiting a little bit for time field
                # If we don't wait, committing the expression will glitch
                try:
                    wait_for(lambda: view.input_select_time.is_displayed, num_sec=6)
                    # It appeared, so if the time is to be set, we will set it
                    # (passing None glitches)
                    if time:
                        view.input_select_time.fill(time)
                except TimedOutError:
                    # Did not appear, ignore that
                    pass
                finally:
                    # And finally, commit the expression :)
                    self.click_commit()
        else:
            self.click_commit()


class GroupTagExpressionEditor(ExpressionEditor):

    @View.nested
    class tag_form_view(View):  # noqa
        tag = BootstrapSelect("chosen_tag")
        value = BootstrapSelect("chosen_value")

    def fill_tag(self, tag=None, value=None):
        """ Fills the 'Tag' type of form.

        Args:
            tag: Name of the field to compare.
            value: Value to check against.
        """
        view = self.tag_form_view
        view.fill(dict(
            tag=tag,
            value=value
        ))
        self.click_commit()


def get_func(name, context):
    """ Return callable from this module by its name.

    Args:
        name: Name of the variable containing the callable.
    Returns: Callable from this module
    """
    assert not name.startswith("_"), "Command '{}' is private!".format(name)
    try:
        func = getattr(context, name)
    except AttributeError:
        raise NameError("Could not find function {} to operate the editor!".format(name))
    try:
        func.__call__
        return func
    except AttributeError:
        raise NameError("{} is not callable!".format(name))


def run_commands(command_list, clear_expression=True, context=None):
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
        clear_expression: Whether to clear the expression before entering new one
        (default `True`)
        context: widget object
    """
    assert isinstance(command_list, list) or isinstance(command_list, tuple)
    step_list = []
    for command in command_list:
        if isinstance(command, six.string_types):
            # Single command, no params
            step_list.append(get_func(command, context))
        elif isinstance(command, dict):
            for key, value in command.items():
                func = get_func(key, context)
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
        context.delete_whole_expression()
    for step in step_list:
        step()


def create_program(dsl_program, widget_object):
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
    SIMPLE_CALL = r"^[a-z_A-Z][a-z_A-Z0-9]*$"  # noqa
    ARGS_CALL = r"^(?P<name>[a-z_A-Z][a-z_A-Z0-9]*)\((?P<args>.*)\)$"  # noqa
    KWARG = r"^[^=]+=.*$"  # noqa
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
    return create_program_from_list(command_list, widget_object)


def create_program_from_list(command_list, widget_object):
    """ Create function which fills the expression from the command list.

    Args:
        command_list: Command list for :py:func:`run_program`
    Returns: Callable, which fills the expression.
    """
    return partial(run_commands, command_list, context=widget_object)
