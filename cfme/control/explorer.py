# -*- coding: utf-8 -*-
"""Page model for Control / Explorer"""
from functools import partial

from cfme.web_ui.menu import nav

from cfme.control.snmp_form import SNMPForm
from cfme.exceptions import CannotContinueWithNavigation
from cfme.web_ui import fill, flash, form_buttons
from cfme.web_ui import Region, Form, Tree, CheckboxTree, Table, Select, EmailSelectForm, \
    CheckboxSelect
from cfme.web_ui.multibox import MultiBoxSelect
from selenium.common.exceptions import NoSuchElementException
from utils.db import cfmedb
from utils.log import logger
from utils.update import Updateable
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.accordion as accordion
import cfme.web_ui.expression_editor as editor
import cfme.web_ui.toolbar as tb


def table_in_object(table_title):
    """If you want to point to tables inside object view, this is what you want to use.

    Works both on down- and upstream.

    Args:
        table_title: Text in `p` element preceeding the table
    Returns: XPath locator for the desired table.
    """
    # Description     paragraph with the text       following element    which is the table
    return "//p[@class='legend' and text()='{}']/following-sibling::*[1][@class='style3']".format(
        table_title
    )

events_table = Table(
    table_locator="//div[@id='event_list_div']//table[@class='style3']"
)
EVENT_NAME_CELL = 1

events_policies_table = Table(
    table_locator="//div[@id='event_info_div']//table[@class='style3']"
)

events_in_policy_table = Table(
    table_locator=table_in_object("Events")
)

condition_folders_table = Table(
    table_locator="//div[@id='condition_folders_div']//table[@class='style3']"
)
CONDITION_FOLDERS_CELL = 1

condition_list_table = Table(
    table_locator="//div[@id='condition_list_div']//table[@class='style3']"
)
CONDITION_LIST_CELL = 1

actions_table = Table(
    table_locator="//div[@id='records_div']//table[@class='style3']"
)

alerts_table = Table(
    table_locator="//div[@id='records_div']//table[@class='style3']"
)

alert_profiles_main_table = Table(
    table_locator="//div[@id='alert_profile_folders_div']//table[@class='style3']"
)

alert_profiles_list_table = Table(
    table_locator="//div[@id='alert_profile_list_div']//table[@class='style3']"
)
ALERT_PROFILES_CELL = 1

visible_tree = Tree("//div[@class='dhxcont_global_content_area']"
                    "[not(contains(@style, 'display: none'))]/div/div/div"
                    "/ul[@class='dynatree-container']")

policies_main_table = Table(
    table_locator="//div[@id='main_div']//table[@class='style3']"
)
POLICIES_MAIN_CELL = 1

policy_profiles_table = Table(
    table_locator="//div[@id='main_div']//table[@class='style3']"
)
POLICY_PROFILES_CELL = 1

policies_table = Table(
    table_locator="//div[@id='records_div']//table[@class='style3']"
)

cfg_btn = partial(tb.select, "Configuration")


def _ap_single_branch(ugly, nice):
    """generates branch for specific Alert Profile"""
    return [
        lambda ctx: accordion_func(
            "Alert Profiles", "All Alert Profiles", "%s Alert Profiles" % nice,
            ctx["alert_profile_name"])(None),
        {
            "%s_alert_profile_edit" % ugly:
            lambda _: cfg_btn("Edit this Alert Profile"),

            "%s_alert_profile_assignments" % ugly:
            lambda _: cfg_btn("Edit assignments for this Alert Profile"),
        }
    ]


def _ap_multi_branch(ugly, nice):
    """Generates branch for listing and adding the profiles"""
    return [
        accordion_func(
            "Alert Profiles", "All Alert Profiles", "%s Alert Profiles" % nice),
        {
            "%s_alert_profile_new" % ugly:
            lambda _: cfg_btn("Add a New")
        }
    ]


def accordion_func(accordion_title, *nodes):
    """Function to click on the accordion and then on the root node of the underlying tree.

    Automatically handles the "blank page" bug.

    Args:
        accordion_title: Text on accordion.
        *nodes: Nodes to click through.
    """
    def f(_):
        try:
            accordion.tree(accordion_title, *nodes)
        except NoSuchElementException:
            raise CannotContinueWithNavigation("blank screen bug!")
    return f

nav.add_branch(
    "control_explorer",
    {
        "control_explorer_policy_profiles":
        [
            accordion_func("Policy Profiles", "All Policy Profiles"),
            {
                "policy_profile_new":
                lambda _: cfg_btn("Add a New Policy Profile")
            }
        ],

        "policy_profile":
        [
            lambda ctx: accordion_func(
                "Policy Profiles", "All Policy Profiles", ctx["policy_profile_name"])(None),
            {   # None because it normally takes a dummy context and returns a function, therefore()
                "policy_profile_edit": lambda _: cfg_btn("Edit this")
            }
        ],

        "host_compliance_policy":
        [
            lambda ctx: accordion_func(
                "Policies", "All Policies", "Compliance Policies",
                "Host Compliance Policies", ctx["policy_name"])(None),
            {
                "host_compliance_policy_edit":
                lambda _: cfg_btn("Edit Basic Info"),

                "host_compliance_policy_events":
                lambda _: cfg_btn("Event assignments"),

                "host_compliance_policy_conditions":
                lambda _: cfg_btn("Condition assignments"),

                "host_compliance_policy_condition_new":
                lambda _: cfg_btn("new Condition"),

                "host_compliance_policy_event":
                [
                    lambda ctx: events_in_policy_table.click_cell(
                        1, ctx["event_name"]
                    ),
                    {
                        "host_compliance_policy_event_actions":
                        lambda _: cfg_btn(
                            "Edit Actions for this Policy Event"
                        ),
                    }
                ],
            }
        ],

        "vm_compliance_policy":
        [
            lambda ctx: accordion_func(
                "Policies", "All Policies", "Compliance Policies",
                "Vm Compliance Policies", ctx["policy_name"])(None),
            {
                "vm_compliance_policy_edit":
                lambda _: cfg_btn("Edit Basic Info"),

                "vm_compliance_policy_events":
                lambda _: cfg_btn("Event assignments"),

                "vm_compliance_policy_conditions":
                lambda _: cfg_btn("Condition assignments"),

                "vm_compliance_policy_condition_new":
                lambda _: cfg_btn("new Condition"),

                "vm_compliance_policy_event":
                [
                    lambda ctx: events_in_policy_table.click_cell(
                        1, ctx["event_name"]
                    ),
                    {
                        "vm_compliance_policy_event_actions":
                        lambda _: cfg_btn(
                            "Edit Actions for this Policy Event"
                        ),
                    }
                ],
            }
        ],

        "host_compliance_policies":
        [
            accordion_func(
                "Policies", "All Policies", "Compliance Policies", "Host Compliance Policies"
            ),
            {
                "host_compliance_policy_new":
                lambda _: cfg_btn("Add a New Host Compliance Policy")
            }
        ],

        "vm_compliance_policies":
        [
            accordion_func(
                "Policies", "All Policies", "Compliance Policies", "Vm Compliance Policies"
            ),
            {
                "vm_compliance_policy_new":
                lambda _: cfg_btn("Add a New Vm Compliance Policy")
            }
        ],

        "host_control_policy":
        [
            lambda ctx: accordion_func(
                "Policies", "All Policies", "Control Policies",
                "Host Control Policies", ctx["policy_name"])(None),
            {
                "host_control_policy_edit":
                lambda _: cfg_btn("Edit Basic Info"),

                "host_control_policy_events":
                lambda _: cfg_btn("Event assignments"),

                "host_control_policy_conditions":
                lambda _: cfg_btn("Condition assignments"),

                "host_control_policy_condition_new":
                lambda _: cfg_btn("new Condition"),

                "host_control_policy_event":
                [
                    lambda ctx: events_in_policy_table.click_cell(
                        1, ctx["event_name"]
                    ),
                    {
                        "host_control_policy_event_actions":
                        lambda _: cfg_btn(
                            "Edit Actions for this Policy Event"
                        ),
                    }
                ],
            }
        ],

        "vm_control_policy":
        [
            lambda ctx: accordion_func(
                "Policies", "All Policies", "Control Policies",
                "Vm Control Policies", ctx["policy_name"])(None),
            {
                "vm_control_policy_edit":
                lambda _: cfg_btn("Edit Basic Info"),

                "vm_control_policy_events":
                lambda _: cfg_btn("Event assignments"),

                "vm_control_policy_conditions":
                lambda _: cfg_btn("Condition assignments"),

                "vm_control_policy_condition_new":
                lambda _: cfg_btn("new Condition"),

                "vm_control_policy_event":
                [
                    lambda ctx: events_in_policy_table.click_cell("description", ctx["event_name"]),
                    {
                        "vm_control_policy_event_actions":
                        lambda _: cfg_btn(
                            "Edit Actions for this Policy Event"
                        ),
                    }
                ],
            }
        ],

        "host_control_policies":
        [
            accordion_func(
                "Policies", "All Policies", "Control Policies", "Host Control Policies"
            ),
            {
                "host_control_policy_new":
                lambda _: cfg_btn("Add a New Host Control Policy")
            }
        ],

        "vm_control_policies":
        [
            accordion_func(
                "Policies", "All Policies", "Control Policies", "Vm Control Policies"
            ),
            {
                "vm_control_policy_new":
                lambda _: cfg_btn("Add a New Vm Control Policy")
            }
        ],

        "control_explorer_events": accordion_func("Events", "All Events"),

        "control_explorer_event":
        lambda ctx: accordion_func("Events", "All Events", ctx["event_name"])(None),

        "host_condition":
        [
            lambda ctx: accordion_func(
                "Conditions", "All Conditions", "Host Conditions", ctx["condition_name"])(None),
            {
                "host_condition_edit":
                lambda _: cfg_btn("Edit this Condition")
            }
        ],

        "vm_condition":
        [
            lambda ctx: accordion_func(
                "Conditions", "All Conditions", "VM Conditions", ctx["condition_name"])(None),
            {
                "vm_condition_edit":
                lambda _: cfg_btn("Edit this Condition")
            }
        ],

        "host_conditions":
        [
            accordion_func("Conditions", "All Conditions", "Host Conditions"),
            {
                "host_condition_new":
                lambda _: cfg_btn("Add a New Host Condition")
            }
        ],

        "vm_conditions":
        [
            accordion_func("Conditions", "All Conditions", "VM Conditions"),
            {
                "vm_condition_new":
                lambda _: cfg_btn("Add a New Vm Condition")
            }
        ],

        "control_explorer_action":
        [
            lambda ctx: accordion_func("Actions", "All Actions", ctx["action_name"])(None),
            {
                "control_explorer_action_edit":
                lambda _: cfg_btn("Edit this Action")
            }
        ],

        "control_explorer_actions":
        [
            accordion_func("Actions", "All Actions"),
            {
                "control_explorer_action_new":
                lambda _: cfg_btn("Add a new Action"),
            },
        ],

        "control_explorer_alert":
        [
            lambda ctx: accordion_func("Alerts", "All Alerts", ctx["alert_name"])(None),
            {
                "control_explorer_alert_edit":
                lambda ctx: cfg_btn("Edit this Alert")
            },
        ],

        "control_explorer_alerts":
        [
            accordion_func("Alerts", "All Alerts"),
            {
                "control_explorer_alert_new":
                lambda _: cfg_btn("Add a New Alert"),
            }
        ],

        "vm_instance_alert_profile": _ap_single_branch("vm_instance", "VM and Instance"),
        "vm_instance_alert_profiles": _ap_multi_branch("vm_instance", "VM and Instance"),

        "server_alert_profile": _ap_single_branch("server", "Server"),
        "server_alert_profiles": _ap_multi_branch("server", "Server"),

        "provider_alert_profile": _ap_single_branch("provider", "Provider"),
        "provider_alert_profiles": _ap_multi_branch("provider", "Provider"),

        "host_alert_profile": _ap_single_branch("host", "Host"),
        "host_alert_profiles": _ap_multi_branch("host", "Host"),

        "datastore_alert_profile": _ap_single_branch("datastore", "Datastore"),
        "datastore_alert_profiles": _ap_multi_branch("datastore", "Datastore"),

        "cluster_alert_profile": _ap_single_branch("cluster", "Cluster"),
        "cluster_alert_profiles": _ap_multi_branch("cluster", "Cluster"),
    }
)


###################################################################################################
# For checking whether passed condition can be assigned to the policy, some class stuff comes here.
###################################################################################################
class _type_check_object(object):
    """This class is used to check, whether one object can be assigned to another."""
    def _is_assignable(self, what):
        if isinstance(self, VMObject):
            return isinstance(what, VMObject)
        elif isinstance(self, HostObject):
            return isinstance(what, HostObject)
        else:
            raise TypeError("Wrong object passed!")


class VMObject(_type_check_object):
    pass


class HostObject(_type_check_object):
    pass


class BaseCondition(Updateable):
    """Base class for conditions.

    They differ just with the navigation prefix, so that is the self.PREFIX which gets changed.

    Usage:
        >> cond = HostCondition("mycond",         # or VMCondition
        ..     expression="fill_count(Host.VMs, >, 50)",
        ..     scope="fill_count(Host.Files, >, 150)")
        >> cond.create()
        >> with update(cond):
        ..     cond.notes = "Important!"
        >> cond.delete()

    Args:
        description: Name of the condition.
        notes: Notes.
        scope: Program, setting the Scope of the Condition.
        expression: Program, setting the Scope of the Expression.
    """
    PREFIX = None

    buttons = Region(
        locators=dict(
            edit_scope="//div[@id='form_scope_div']//img[@alt='Edit this Scope']",
            edit_expression="//div[@id='form_expression_div']//img[@alt='Edit this Expression']",
        )
    )

    form = Form(
        fields=[
            ("description", "//input[@id='description']"),
            ("notes", "//textarea[@id='notes']"),
        ]
    )

    def __init__(self,
                 description,
                 notes=None,
                 scope=None,
                 expression=None):
        if not self.PREFIX:
            raise NotImplementedError("You must use an inherited class from %s"
                                      % self.__class__.__name__)
        self.description = description
        self.notes = notes
        self.scope = scope
        self.expression = expression

    @property
    def exists(self):
        conditions = cfmedb["conditions"]
        return cfmedb.session\
            .query(conditions.description)\
            .filter(conditions.description == self.description)\
            .count() > 0

    def _do_expression_editing(self):
        """Fills the expression field using the mini-programs."""
        if self.expression is not None:
            if not self.is_editing_expression:
                sel.click(self.buttons.edit_expression)
            editor.create_program(self.expression)()

    def _do_scope_editing(self):
        """Fills the scope field using the mini-program."""
        if self.scope is not None:
            if not self.is_editing_scope:
                sel.click(self.buttons.edit_scope)
            editor.create_program(self.scope)()

    def create(self, cancel=False):
        """Creates new Condition according to the informations filed in constructor.

        Args:
            cancel: Whether to cancel the process instead of saving.
        """
        sel.force_navigate(self.PREFIX + "condition_new")
        self._do_expression_editing()
        self._do_scope_editing()
        action = form_buttons.cancel if cancel else form_buttons.add
        fill(self.form, dict(description=self.description, notes=self.notes), action=action)
        flash.assert_no_errors()

    def update(self, updates, cancel=False):
        """Updates the informations in the object and then updates the Condition in CFME.

        Args:
            updates: Provided by update() context manager.
            cancel: Whether to cancel the process instead of saving.
        """
        sel.force_navigate(self.PREFIX + "condition_edit",
                           context=dict(condition_name=self.description))
        if "description" in updates:
            self.description = updates["description"]

        if "notes" in updates:
            self.notes = updates["notes"]

        if "scope" in updates:
            self.scope = updates["scope"]
            self._do_scope_editing()

        if "expression" in updates:
            self.expression = updates["expression"]
            self._do_expression_editing()

        action = form_buttons.cancel if cancel else form_buttons.save
        fill(self.form, dict(description=self.description, notes=self.notes), action=action)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        """Deletes the condition in CFME.

        Args:
            cancel: Whether to cancel the process instead of saving.
        """
        sel.force_navigate(self.PREFIX + "condition",
                           context=dict(condition_name=self.description))
        cfg_btn("Delete this", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()

    @property
    def is_editing_scope(self):
        """Is editor for Scope displayed?

        Returns: :py:class:`bool`
        """
        self._wait_form_displayed()
        return sel.is_displayed(self.buttons.edit_expression)

    @property
    def is_editing_expression(self):
        """Is editor for Expression displayed?

        Returns: :py:class:`bool`
        """
        self._wait_form_displayed()
        return sel.is_displayed(self.buttons.edit_scope)

    def _wait_form_displayed(self):
        """The buttons for choosing Scope or Expression appear a bit later, so we have to wait."""
        return sel.wait_for_element(self.buttons.edit_scope, self.buttons.edit_expression)


class VMCondition(BaseCondition, VMObject):
    PREFIX = "vm_"


class HostCondition(BaseCondition, HostObject):
    PREFIX = "host_"


class BasePolicy(Updateable):
    PREFIX = None

    assigned_conditions = Table(
        table_locator=table_in_object("Conditions")
    )

    assigned_events = Table(
        table_locator=table_in_object("Events")
    )

    form = Form(
        fields=[
            ("description", "//input[@id='description']"),
            ("active", "//input[@id='active']"),
            ("notes", "//textarea[@id='notes']"),
        ]
    )

    conditions = MultiBoxSelect.default()

    # Event action assignment
    event_actions = Form(
        fields=[
            (
                "true",
                MultiBoxSelect(
                    "//select[@id='choices_chosen_true']",
                    "//select[@id='members_chosen_true']",
                    "//a[contains(@href, 'true')]/img[contains(@alt, 'Remove selected')]",
                    "//a[contains(@href, 'true')]/img[contains(@alt, 'Move selected')]",
                    "//a[contains(@href, 'true')]/img[contains(@alt, 'Remove all')]",
                )
            ),
            (
                "false",
                MultiBoxSelect(
                    "//select[@id='choices_chosen_false']",
                    "//select[@id='members_chosen_false']",
                    "//a[contains(@href, 'false')]/img[contains(@alt, 'Remove selected')]",
                    "//a[contains(@href, 'false')]/img[contains(@alt, 'Move selected')]",
                    "//a[contains(@href, 'false')]/img[contains(@alt, 'Remove all')]",
                )
            ),
        ]
    )

    def __init__(self,
                 description,
                 active=True,
                 notes=None,
                 scope=None):
        if not self.PREFIX:
            raise NotImplementedError("You must use an inherited class from %s"
                                      % self.__class__.__name__)
        self.description = description
        self.notes = notes
        self.active = active
        self.scope = scope

    @property
    def exists(self):
        policies = cfmedb["miq_policies"]
        return cfmedb.session\
            .query(policies.description)\
            .filter(policies.description == self.description)\
            .count() > 0

    @property
    def _on_detail_page(self):
        raise NotImplementedError("You must implement this in inherited class")

    def create(self, cancel=False):
        """Creates new Condition according to the informations filed in constructor.

        Args:
            cancel: Whether to cancel the process instead of saving.
        """
        sel.force_navigate(self.PREFIX + "policy_new")
        if self.scope is not None:
            editor.create_program(self.scope)()
        action = form_buttons.cancel if cancel else form_buttons.add
        fill(
            self.form,
            dict(
                description=self.description,
                notes=self.notes,
                active=self.active
            ),
            action=action)
        flash.assert_no_errors()

    def update(self, updates, cancel=False):
        """Updates the informations in the object and then updates the Condition in CFME.

        Args:
            updates: Provided by update() context manager.
            cancel: Whether to cancel the process instead of saving.
        """
        sel.force_navigate(self.PREFIX + "policy_edit",
                           context=dict(policy_name=self.description))
        if "description" in updates:
            self.description = updates["description"]

        if "notes" in updates:
            self.notes = updates["notes"]

        if "scope" in updates:
            self.scope = updates["scope"]
            editor.create_program(self.scope)()

        action = form_buttons.cancel if cancel else form_buttons.save
        fill(
            self.form,
            dict(
                description=self.description,
                notes=self.notes,
                active=self.active
            ),
            action=action)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        """Deletes the condition in CFME.

        Args:
            cancel: Whether to cancel the process instead of saving.
        """
        sel.force_navigate(self.PREFIX + "policy", context=dict(policy_name=self.description))
        cfg_btn("Delete this", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()

    def assign_conditions(self, *conditions):
        """Assign one or more conditions to this Policy.

        If using the :py:class:`BaseCondition` assignment, you must provide a correct type of
        condition (you cannot assign eg. :py:class:`VMCondition` to :py:class:`HostControlPolicy`).

        Args:
            *conditions: Each condition can be either :py:class:`str` or :py:class:`BaseCondition`
                instance.
        """
        assign_names = []
        for condition in conditions:
            if isinstance(condition, BaseCondition):
                if not self._is_assignable(condition):
                    raise TypeError("You cannot add VM object to Host and vice versa!")
                # Assign condition.description
                logger.debug(
                    "Assigning condition `%s` to policy `%s`" % (condition.description,
                                                                 self.description))
                if not condition.exists:
                    condition.create()
                    assert condition.exists, "Could not create the condition!"
                assign_names.append(condition.description)
            elif isinstance(condition, basestring):
                # assign condition
                logger.debug(
                    "Assigning condition `%s` to policy `%s`" % (condition,
                                                                 self.description))
                assign_names.append(condition)
            else:
                raise TypeError("assign_conditions() accepts only BaseCondition and basestring")
        sel.force_navigate(self.PREFIX + "policy_conditions",
                           context=dict(policy_name=self.description))
        fill(self.conditions, assign_names)
        form_buttons.save()
        flash.assert_no_errors()
        return self

    def is_condition_assigned(self, condition):
        """Check whether the provided condition is assigned to the Policy.

        Args:
            condition: Condition to check. Can be either :py:class:`str` or the
                :py:class:`BaseCondition` object.
        Returns: :py:class:`bool` - `True` if present, `False` if not.
        """
        if isinstance(condition, basestring):
            condition_name = condition
        elif isinstance(condition, BaseCondition):
            if not self._is_assignable(condition):
                return False  # Cannot be, obviously ...
            condition_name = condition.description
        else:
            raise TypeError("is_condition_assigned accepts string or BaseCondition object only!")
        sel.force_navigate(self.PREFIX + "policy",
                           context=dict(policy_name=self.description))
        try:
            sel.move_to_element(self.assigned_conditions)
            return bool(self.assigned_conditions.find_cell("description", condition_name))
        except NoSuchElementException:
            return False

    def is_event_assigned(self, event):
        """Check whether the provided event is assigned to the Policy.

        Args:
            event: Event to check. :py:class:`str`.

        Returns: :py:class:`bool` - `True` if present, `False` if not.
        """
        sel.force_navigate(self.PREFIX + "policy",
                           context=dict(policy_name=self.description))
        try:
            sel.move_to_element(self.assigned_events)
            return bool(self.assigned_events.find_cell("description", event))
        except NoSuchElementException:
            return False

    def assign_actions_to_event(self, event, actions):
        """This method takes a list or dict of actions, goes into the policy event and assigns them.

        Actions can be passed both as the objects, but they can be passed also as a string.
        Actions, passed as an object but not created yet, will be created.
        If the specified event is not assigned to the policy, it will be assigned.

        Args:
            event: Name of the event under which the actions will be assigned.
            actions: If :py:class:`list` (or similar), all of these actions will be set under
                TRUE section. If :py:class:`dict`, the action is key and value specifies its
                placement. If it's True, then it will be put in the TRUE section and so on.

        """
        true, false = [], []
        if isinstance(actions, list) or isinstance(actions, tuple) or isinstance(actions, set):
            true.extend(actions)
        elif isinstance(actions, dict):
            for action, is_true in actions.iteritems():
                if is_true:
                    true.append(action)
                else:
                    false.append(action)
        else:
            raise TypeError("assign_actions_to_event expects, list, tuple, set or dict!")
        # Check whether actions exist
        for action in true + false:
            if isinstance(action, Action):
                if not action.exists:
                    action.create()
                    assert action.exists, "Could not create action %s!" % action.description
            else:  # string
                if not Action(action, "Tag").exists:
                    raise NameError("Action with name %s does not exist!" % action)
        # Check whether we have all necessary events assigned
        if not self.is_event_assigned(event):
            self.assign_events(event, do_not_uncheck=True)
            assert self.is_event_assigned(event), "Could not assign event %s!" % event
        # And now we can assign actions
        sel.force_navigate(self.PREFIX + "policy_event_actions",
                           context=dict(policy_name=self.description, event_name=event))
        fill(
            self.event_actions,
            dict(
                true=[str(action) for action in true],
                false=[str(action) for action in false],
            )
        )
        form_buttons.save()
        flash.assert_no_errors()


class BaseControlPolicy(BasePolicy):
    events = CheckboxSelect("//div[@id='policy_info_div']")

    def assign_events(self, *events, **kwargs):
        """(un)Assign one or more events to this Policy.

        Args:
            *events: Each event is represented by :py:class:`str`. If it is present, it will be
                checked. If it is not present, it will be unchecked.
        Keywords:
            do_not_uncheck: If specified and True, no unchecking will happen.
        """
        sel.force_navigate(self.PREFIX + "policy_events",
                           context=dict(policy_name=self.description))
        if not kwargs.get("do_not_uncheck", False):
            fill(self.events, False)
        fill(self.events, {sel.ByText(event) for event in events})
        form_buttons.save()
        flash.assert_no_errors()


class HostCompliancePolicy(BasePolicy, HostObject):
    PREFIX = "host_compliance_"

    def __str__(self):
        return "Host Compliance: %s" % self.description


class VMCompliancePolicy(BasePolicy, VMObject):
    PREFIX = "vm_compliance_"

    def __str__(self):
        return "VM and Instance Compliance: %s" % self.description


class HostControlPolicy(BaseControlPolicy, HostObject):
    PREFIX = "host_control_"

    def __str__(self):
        return "Host Control: %s" % self.description


class VMControlPolicy(BaseControlPolicy, VMObject):
    PREFIX = "vm_control_"

    def __str__(self):
        return "VM and Instance Control: %s" % self.description


class Alert(Updateable):
    """Alert representation object.

    Example:

        >>> alert = Alert("my_alert", timeline_event=True, driving_event="Hourly Timer")
        >>> alert.create()
        >>> alert.delete()

    Args:
        description: Name of the Alert.
        based_on: Cluster, Datastore, Host, Provider, ...
        evaluate: If specified as :py:class:`str`, it will select 'Expression (Custom)' and compile
            the string into the program which selects the expression. If specified as callable
            (something that has ``.__call__`` method inside), then it will also select the custom
            expression and will use the function to fill the expression. If specified as tuple(list)
            it will use it as follows: ``("What to Evaluate selection", dict(values="for form"))``.
            If you want to select Nothing, you will therefore pass ``("Nothing", {})``.

            Other example:
                .. code-block:: python

                    ("Hardware Reconfigured",
                     dict(hw_attribute="Number of CPUs", hw_attribute_operator="Increased")
                    )

            For all fields, check the `form` class variable.
        driving_event: This Alert's driving event (Hourly Timer, ...).
        notification_frequency: 1 Minute, 2 Minutes, ...
        snmp_trap: Values for :py:class:`cfme.web_ui.snmp_form.SNMPForm`. If `False`, it is disabled
        emails: Whether to send e-mails. `False` disables, string or list of strings
            with emails enables.
        timeline_event: Whether generate a timeline event.
        mgmt_event: If specified as string, it will reveal teh form and types it into the text box.
            If False, then it will be disabled. None - don't care.

    Note:
        If you don't specify the 'master' option or set it False (like snmp_trap for
        snmp_trap_hosts), the dependent variables will be None'd to ensure that things like
        :py:class:`NoSuchElementException` do not happen.
    """
    manual_email = Region(
        locators=dict(
            field="//input[@id='email']",
            add="//img[@alt='Add'][contains(@onclick, 'add_email')]",
            present_emails="//a[contains(@href, 'remove_email')]"
        )
    )

    form = Form(
        fields=[
            ("description", "//input[@id='description']"),
            ("active", "//input[@id='enabled_cb']"),
            ("based_on", Select("//select[@id='miq_alert_db']")),
            ("evaluate", Select("//select[@id='exp_name']")),
            ("driving_event", Select("//select[@id='exp_event']")),
            ("based_on", Select("//select[@id='miq_alert_db']")),
            ("notification_frequency", Select("//select[@id='repeat_time']")),
            # Different evaluations begin
            # Event log threshold
            ("event_log_message_type",
                Select("//select[@id='select_event_log_message_filter_type']")),
            ("event_log_message_value", "//input[@id='event_log_message_filter_value']"),
            ("event_log_name", "//input[@id='event_log_name']"),
            ("event_log_level", "//input[@id='event_log_level']"),
            ("event_log_event_id", "//input[@id='event_log_event_id']"),
            ("event_log_source", "//input[@id='event_log_source']"),
            ("event_time_threshold", Select("//select[@id='time_threshold']")),  # shared
            ("event_count_threshold", "//input[@id='freq_threshold']"),  # shared
            # Event threshold (uses the shared fields from preceeding section)
            ("event_type", Select("//select[@id='event_types']")),
            # HW reconfigured + VM Value Changed
            ("hw_attribute", Select("//select[@id='select_hdw_attr']")),
            ("hw_attribute_operator", "//select[@id='select_operator']"),
            # Normal operating range
            ("performance_field", Select("//select[@id='perf_column']")),
            ("performance_field_operator", Select("//select[@id='select_operator']")),
            ("performance_time_threshold", Select("//select[@id='rt_time_threshold']")),
            # Real Time Performance (uses fields from previous)
            ("performance_field_value", "//input[@id='value_threshold']"),
            ("performance_trend", Select("//select[@id='trend_direction']")),
            ("performance_debug_trace", Select("//select[@id='debug_trace']")),
            # VMWare alarm
            ("vmware_alarm_provider", Select("//select[@id='select_ems_id']")),
            ("vmware_alarm_type", Select("//select[@id='select_ems_alarm_mor']")),
            # Different evaluations end
            ("send_email", "//input[@id='send_email_cb']"),
            ("emails", EmailSelectForm()),
            ("snmp_trap_send", "//input[@id='send_snmp_cb']"),
            ("snmp_trap", SNMPForm()),
            ("timeline_event", "//input[@id='send_evm_event_cb']"),
            ("mgmt_event_send", "//input[@id='send_event_cb']"),
            ("mgmt_event", "//input[@id='event_name']"),
        ]
    )

    def __init__(self,
                 description,
                 active=None,
                 based_on=None,
                 evaluate=None,
                 driving_event=None,
                 notification_frequency=None,
                 snmp_trap=None,
                 emails=None,
                 timeline_event=None,
                 mgmt_event=None):
        for key, value in locals().iteritems():
            if key == "self":
                continue
            setattr(self, key, value)

    def __str__(self):
        """Conversion to string used when assigning in multibox selector."""
        return self.description

    @property
    def exists(self):
        alerts = cfmedb["miq_alerts"]
        return cfmedb.session\
            .query(alerts.description)\
            .filter(alerts.description == self.description)\
            .count() > 0

    def create(self, cancel=False):
        sel.force_navigate("control_explorer_alert_new")
        self._fill()
        if cancel:
            form_buttons.cancel()
        else:
            form_buttons.add()
        flash.assert_no_errors()

    def update(self, updates, cancel=False):
        """Update the object with new values and save.

        Args:
        updates: Provided by update() context manager.
            cancel: Whether to cancel the update (default False).
        """
        for key, value in updates.iteritems():
            if key in {"self", "cancel"}:
                continue
            try:
                getattr(self, key)
                if value is not None:
                    setattr(self, key, value)
            except AttributeError:
                pass
        # Go update!
        sel.force_navigate("control_explorer_alert_edit",
                           context={"alert_name": self.description})
        self._fill()
        if cancel:
            form_buttons.cancel()
        else:
            form_buttons.save()
        flash.assert_no_errors()

    def delete(self, cancel=False):
        """Delete this Alert from CFME.

        Args:
            cancel: Whether to cancel the deletion (default False).
        """
        sel.force_navigate("control_explorer_alert", context={"alert_name": self.description})
        cfg_btn("Delete this Alert", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()

    def _fill(self):
        """This function prepares the values and fills the form."""
        fill_details = dict(
            description=self.description,
            active=self.active,
            based_on=self.based_on,
            driving_event=self.driving_event,
            notification_frequency=self.notification_frequency,
            timeline_event=self.timeline_event,
        )
        # Hideable sections:
        if self.snmp_trap is not None:
            # We have to check or uncheck the checkbox and then subsequently handle the form fill
            if self.snmp_trap is False:
                fill_details["snmp_trap_send"] = False
                fill_details["snmp_trap"] = None
            else:
                fill_details["snmp_trap_send"] = True
                fill_details["snmp_trap"] = self.snmp_trap
        if self.emails is not None:
            # We have to check or uncheck the checkbox and then subsequently handle the form fill
            if self.emails is False:
                fill_details["send_email"] = False
                fill_details["emails"] = None
            else:
                fill_details["send_email"] = True
                fill_details["emails"] = self.emails
        if self.mgmt_event is not None:
            # We have to check or uncheck the checkbox and then subsequently handle the form fill
            if self.mgmt_event is False:
                fill_details["mgmt_event_send"] = False
                fill_details["mgmt_event"] = None
            else:
                fill_details["mgmt_event_send"] = True
                fill_details["mgmt_event"] = self.mgmt_event
        # Evaluate expression
        form_func = lambda: None
        if self.evaluate:
            if isinstance(self.evaluate, basestring):
                # String -> compile program
                fill_details["evaluate"] = "Expression (Custom)"
                form_func = editor.create_program(self.evaluate)
            elif hasattr(self.evaluate, "__call__"):
                # Callable
                fill_details["evaluate"] = "Expression (Custom)"
                form_func = self.evaluate
            elif isinstance(self.evaluate, tuple) or isinstance(self.evaluate, list):
                # Tuple -> dropdown select + the values in the form which will appear
                assert len(self.evaluate) == 2, "evaluate must have length of 2"
                fill_details["evaluate"], evaluate_values = self.evaluate
                assert isinstance(evaluate_values, dict), "The values for evaluate must be dict!"
                fill_details.update(evaluate_values)
            else:
                raise TypeError("evaluate must be either string with dropdown value or function "
                                "or a 2-tuple with (dropdown value, dict of values to set)")
        fill(self.form, fill_details)
        form_func()     # Fill the expression if present


class Action(Updateable):
    """This class represents one Action.

    Example:

        >>> from cfme.control.explorer import Action
        >>> action = Action("some_action",
        ...     "Tag", dict(tag=("My Company Tags", "Department", "Accounting")))
        >>> action.create()
        >>> action.delete()

    Args:
        description: Action name.
        action_type: Type of the action, value from the dropdown select.
        action_values: :py:class:`dict` with values to give to the sub-form (in Actions.forms).
            See the dictionary for further details. If you fill the `Tag` section, you have to pass
            the tuple or list with parameters for :py:meth:`Tree.click_path` for Tag selection.
            For `Evaluate Alerts`, you have to pass an iterable with list of alerts to select.

    """
    form = Form(
        fields=[
            ("description", "//input[@id='description']"),
            ("action_type", Select("//select[@id='miq_action_type']")),
            # Evaluate Alerts (TODO)
        ]
    )

    sub_forms = {
        "Assign Profile to Analysis Tasks":
        Form(
            fields=[
                ("analysis_profile", Select("//select[@id='analysis_profile']")),
            ]
        ),

        "Create a Snapshot":
        Form(
            fields=[
                ("snapshot_name", "//input[@id='snapshot_name']"),
            ]
        ),

        "Delete Snapshots by Age":
        Form(
            fields=[
                ("snapshot_age", Select("//select[@id='snapshot_age']")),
            ]
        ),

        "Inherit Parent Tags":
        Form(
            fields=[
                ("parent_type", Select("//select[@id='parent_type']")),
                ("tags", CheckboxSelect(
                    "//*[@id='action_options_div']/fieldset/table/tbody/tr[2]/td[2]/table")),
            ]
        ),

        "Invoke a Custom Automation":
        Form(
            fields=[
                ("message", "//input[@id='object_message']"),
                ("request", "//input[@id='object_request']"),
                ("attribute_1", "//input[@id='attribute_1']"),
                ("value_1", "//input[@id='value_1']"),
                ("attribute_2", "//input[@id='attribute_2']"),
                ("value_2", "//input[@id='value_2']"),
                ("attribute_3", "//input[@id='attribute_3']"),
                ("value_3", "//input[@id='value_3']"),
                ("attribute_4", "//input[@id='attribute_4']"),
                ("value_4", "//input[@id='value_4']"),
                ("attribute_5", "//input[@id='attribute_5']"),
                ("value_5", "//input[@id='value_5']"),
            ]
        ),

        "Reconfigure CPUs":
        Form(
            fields=[
                ("num_cpus", Select("//select[@id='cpu_value']")),
            ]
        ),

        "Reconfigure Memory":
        Form(
            fields=[
                ("memory_size", Select("//select[@id='memory_value']")),
            ]
        ),

        "Remove Tags":
        CheckboxSelect(
            "//div[@id='action_options_div']//td[@class='key' and .='Categories']"
            "/../td/table/tbody"
        ),

        "Send an E-mail":
        Form(
            fields=[
                ("from", "//input[@id='from']"),
                ("to", "//input[@id='to']"),
            ]
        ),

        "Set a Custom Attribute in vCenter":
        Form(
            fields=[
                ("attribute", "//input[@id='attribute']"),
                ("value", "//input[@id='value']"),
            ]
        ),

        "Send an SNMP Trap":
        SNMPForm(),

        "Tag":
        Form(
            fields=[
                (
                    "tag",
                    Tree(
                        "//div[@id='action_tags_treebox']/div/table"    # Old builds
                        "|"
                        "//div[@id='action_tags_treebox']/ul",          # New builds
                    )
                ),
            ]
        ),

        "Evaluate Alerts": MultiBoxSelect.default()
    }

    def __init__(self, description, action_type, action_values=None):
        assert action_type in self.sub_forms.keys(), "Unrecognized Action Type (%s)" % action_type
        self.description = description
        self.action_type = action_type
        self.action_values = action_values or self._default_values

    def __str__(self):
        return self.description

    @property
    def exists(self):
        actions = cfmedb["miq_actions"]
        return cfmedb.session\
            .query(actions.description)\
            .filter(actions.description == self.description)\
            .count() > 0

    @property
    def _default_values(self):
        """This property provides a default value depending on action_type."""
        if self.action_type == "Tag":
            return tuple()
        else:
            return dict()

    def _fill(self, action):
        """This method handles filling of the form. Handles differences between some types
        of forms."""
        fill(self.form, dict(description=self.description, action_type=self.action_type))
        if self.sub_forms[self.action_type] is not None:
            fill(self.sub_forms[self.action_type], self.action_values)
            action()
            flash.assert_no_errors()
        else:
            raise Exception("You must specify action_type!")

    def create(self, cancel=False):
        """Create this Action in UI.

        Args:
            cancel: Whether to cancel the creation (default False).
        """
        sel.force_navigate("control_explorer_action_new")
        action = form_buttons.cancel if cancel else form_buttons.add
        return self._fill(action)

    def update(self, updates, cancel=False):
        """Update this Action in UI.

        Args:
            updates: Provided by update() context manager.
            cancel: Whether to cancel the update (default False).
        """
        sel.force_navigate("control_explorer_action_edit",
                           context={"action_name": self.description})
        action = form_buttons.cancel if cancel else form_buttons.save
        if "description" in updates:
            self.description = updates["description"]

        if "action_type" in updates and updates["action_type"] != self.action_type:
            action_type = updates["action_type"]
            logger.debug("Changing action_type for Action %s" % self.description)
            assert action_type in self.sub_forms.keys(), "Unk. Action Type (%s)" % action_type
            self.action_type = action_type
            self.action_values = self._default_values
        if "action_values" in updates:
            if isinstance(self.action_values, dict):
                self.action_values.update(updates["action_values"])
            else:
                # tuple or list for Tag selector
                self.action_values = updates["action_values"]

        return self._fill(action)

    def delete(self, cancel=False):
        """Delete this Action in UI.

        Args:
            cancel: Whether to cancel the deletion (default False).
        """
        sel.force_navigate("control_explorer_action",
                           context={"action_name": self.description})
        cfg_btn("Delete this Action", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()


class PolicyProfile(Updateable):
    """This class represents a Policy Profile.

    Policies can be assigned to Policy Profile and also the Policy Profile.

    Example:

        >> from cfme.control.explorer import PolicyProfile, HostControlPolicy, VMCompliancePolicy
        >> profile = PolicyProfile("some_profile",
        ..     policies=[HostControlPolicy("funny"), VMCompliancePolicy("things")])
        >> profile.create()
        >> with update(profile):
        ..     profile.notes = "notes!"
        >> profile.delete()

    Args:
        description: Name of the Alert Profile.
        policies: Iterable with policies. Can be of :py:class:`str` but also objects of
            :py:class:`BasePolicy` can be used, then Policy Profile checks for presence of policies
            and if they aren't created yet, it will create them.
        notes: Notes for the Policy Profile.
    """
    form = Form(
        fields=[
            ("description", "//input[@id='description']"),
            ("notes", "//textarea[@id='notes']"),
            ("policies", MultiBoxSelect.default())
        ]
    )

    def __init__(self, description, policies=None, notes=None):
        self.policies = policies
        self.description = description
        self.notes = notes

    @property
    def exists(self):
        """Check existence of this Policy Profile.

        Returns: :py:class:`bool` signalizing the presence of the Policy Profile in database.
        """
        miq_sets = cfmedb["miq_sets"]
        return cfmedb.session\
            .query(miq_sets.description)\
            .filter(
                miq_sets.description == self.description and miq_sets.set_type == "MiqPolicySet"
            )\
            .count() > 0

    def create(self, cancel=False):
        """Create this Policy Profile.

        Args:
            cancel: Whether to cancel the operation.
        """
        policy_list = []
        for policy in self.policies:
            if isinstance(policy, BasePolicy):
                if not policy.exists:
                    policy.create()
                    assert policy.exists, "Unable to create a policy %s!" % str(policy)
            policy_list.append(str(policy))
        sel.force_navigate("policy_profile_new")
        fill(
            self.form,
            dict(description=self.description, notes=self.notes, policies=policy_list),
            action=form_buttons.cancel if cancel else form_buttons.add
        )
        flash.assert_no_errors()

    def update(self, updates, cancel=False):
        """Update informations, verify presence of policies, navigate to page and update the info.

        Args:
            updates: Provided by update() context manager.
            cancel: Whether to cancel the update.
        """
        if "description" in updates:
            self.description = updates["description"]

        policy_list = None
        if "policies" in updates:
            self.policies = updates["policies"]
            policy_list = []
            for policy in self.policies:
                if isinstance(policy, BasePolicy):
                    if not policy.exists:
                        policy.create()
                        assert policy.exists, "Unable to create a policy %s!" % str(policy)
                policy_list.append(str(policy))
        if "notes" in updates:
            self.notes = updates["notes"]
        sel.force_navigate("policy_profile_edit", context={"policy_profile_name": self.description})
        fill(
            self.form,
            dict(description=self.description, notes=self.notes, policies=policy_list)
        )
        form_buttons.cancel() if cancel else form_buttons.save()
        flash.assert_no_errors()

    def delete(self, cancel=False):
        """Delete this Policy Profile. Does not delete child policies.

        Args:
            cancel: Whether to cancel the operation.
        """
        sel.force_navigate("policy_profile", context={"policy_profile_name": self.description})
        cfg_btn("Remove this Policy Profile", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()


class BaseAlertProfile(Updateable):
    """This class represents an Alert Profile.

    Alerts can be assigned to Alert Profile and also the Alert Profile can be assigned to various
    objects.

    Example:

        >> from cfme.control.explorer import Alert, VMInstanceAlertProfile
        >> p = VMInstanceAlertProfile("aprofile",
        ..     alerts=[Alert("somealert", timeline_event=True, driving_event="Hourly Timer")])
        >> p.create()
        >> p.assign_to("The Enterprise")
        >> with update(p):
        ..     p.notes = "Notes!"
        >> p.delete()

    Args:
        description: Name of the Alert Profile.
        alerts: Iterable with alerts. Can be of :py:class:`str` but also objects of
            :py:class:`Alert` can be used, then Alert Profile checks for presence of alerts and
            if they aren't created yet, it will create them.
        notes: Notes for the Alert Profile.
    """
    PREFIX = None

    form = Form(
        fields=[
            ("description", "//input[@id='description']"),
            ("notes", "//textarea[@id='notes']"),
            ("alerts", MultiBoxSelect.default())
        ]
    )

    selected_form = Form(
        fields=[
            ("selections",
             CheckboxTree("//div[@id='obj_treebox']/div/table|//div[@id='obj_treebox']/ul"))]
    ),

    buttons = Region(
        locators=dict(
            add="//div[@id='buttons_on']//img[@alt='Add']",
            cancel="//div[@id='buttons_on']//img[@alt='Cancel']",
            save="//div[@id='buttons_on']//img[@alt='Save Changes']",
            reset="//div[@id='buttons_on']//img[@alt='Reset Changes']",
        )
    )

    assignments = Form(
        fields=[
            ("assign", Select("//select[@id='chosen_assign_to']")),
        ]
    )

    sub_assignments = {
        "<Nothing>": Form(fields=[]),
        "The Enterprise": Form(fields=[]),
        "Selected Clusters": selected_form,
        "Selected Folders": selected_form,
        "Selected Hosts": selected_form,
        "Selected Infrastructure Providers": selected_form,
        "Selected Resource Pools": selected_form,
        "Selected Hosts": selected_form,
        "Tagged Clusters": selected_form,
        "Tagged Hosts": selected_form,
        "Tagged Clusters": selected_form,
        "Tagged Infrastructure Providers": selected_form,
        "Tagged Clusters": selected_form,
        "Tagged Resource Pools": selected_form,
        "Tagged VMs and Instances": selected_form
    }

    def __init__(self, description, alerts=None, notes=None):
        assert self.PREFIX, "You must use inherited class of this!"
        self.alerts = alerts
        self.description = description
        self.notes = notes

    @property
    def exists(self):
        """Check existence of this Alert Profile.

        Returns: :py:class:`bool` signalizing the presence of the Alert Profile in database.
        """
        miq_sets = cfmedb["miq_sets"]
        return cfmedb.session\
            .query(miq_sets.description)\
            .filter(
                miq_sets.description == self.description and miq_sets.set_type == "MiqAlertSet"
            )\
            .count() > 0

    def create(self, cancel=False):
        """Create this Alert Profile.

        Args:
            cancel: Whether to cancel the operation.
        """
        for alert in self.alerts:
            if isinstance(alert, Alert) and not alert.exists:
                alert.create()
                assert alert.exists, "Could not create an Alert!"
        sel.force_navigate("%s_alert_profile_new" % self.PREFIX)
        fill(self.form, dict(
            description=self.description,
            notes=self.notes,
            alerts=self.alerts,
        ))
        if not cancel:
            form_buttons.add()
        else:
            form_buttons.cancel()
        flash.assert_no_errors()

    def update(self, updates, cancel=False):
        """ Update informations, verify presence of alerts, navigate to page and update the info.

        Args:
            updates: Provided by update() context manager.
            cancel: Whether to cancel the update.
        """
        if "description" in updates:
            self.description = updates["description"]

        if "alerts" in updates:
            self.alerts = updates["alerts"]
            for alert in self.alerts:
                if isinstance(alert, Alert) and not alert.exists:
                    alert.create()
                    assert alert.exists, "Could not create an Alert!"
        if "notes" in updates:
            self.notes = updates["notes"]
        sel.force_navigate("%s_alert_profile_edit" % self.PREFIX,
                           context={"alert_profile_name": self.description})
        fill(self.form, dict(
            description=self.description,
            notes=self.notes,
            alerts=self.alerts,
        ))
        if not cancel:
            form_buttons.save()
        else:
            form_buttons.cancel()
        flash.assert_no_errors()

    def delete(self, cancel=False):
        """Delete this Alert Profile. Does not delete child Alerts.

        Args:
            cancel: Whether to cancel the operation.
        """
        sel.force_navigate("%s_alert_profile" % self.PREFIX,
                           context={"alert_profile_name": self.description})
        cfg_btn("Delete this Alert Profile", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()

    def assign_to(self, assign, selections=None, tag_category=None):
        """Assigns this Alert Profile to specified objects.

        Args:
            assign: Where to assign (The Enterprise, ...).
            selections: What items to check in the tree. N/A for The Enteprise.
            tag_category: Only for choices starting with Tagged. N/A for The Enterprise.
        """
        sel.force_navigate("%s_alert_profile_assignments" % self.PREFIX,
                           context={"alert_profile_name": self.description})
        fill(self.assignments, dict(assign=assign))
        if selections or tag_category:
            fill(self.sub_assignments[assign], dict(category=tag_category, selections=selections))
        form_buttons.save()
        flash.assert_no_errors()


class ClusterAlertProfile(BaseAlertProfile):
    PREFIX = "cluster"


class DatastoreAlertProfile(BaseAlertProfile):
    PREFIX = "datastore"


class HostAlertProfile(BaseAlertProfile):
    PREFIX = "host"


class ProviderAlertProfile(BaseAlertProfile):
    PREFIX = "provider"


class ServerAlertProfile(BaseAlertProfile):
    PREFIX = "server"


class VMInstanceAlertProfile(BaseAlertProfile):
    PREFIX = "vm_instance"


def event_policies(event):
    """Return all policies, where specified event is assigned.

    Args:
        event: Event to examine.

    Returns: :py:class:`set` of the policies where this event is assigned.
    """
    sel.force_navigate("control_explorer_event", context={"event_name": event})
    try:
        return {policy[1].text.encode("utf-8").strip() for policy in events_policies_table.rows()}
    except NoSuchElementException:
        return set([])
