#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import ui_navigate as nav
import cfme
import cfme.web_ui.menu  # so that menu is already loaded before grafting onto it

from cfme.web_ui import fill
from cfme.web_ui import Region, Form, Tree, Table
from selenium.webdriver.common.by import By
from utils.log import logger
from utils.text import normalize_text
from utils.update import Updateable
from utils.wait import wait_for, TimedOutError
import cfme.fixtures.pytest_selenium as browser
import cfme.web_ui.accordion as accordion
import cfme.web_ui.expression_editor as editor
import cfme.web_ui.flash as flash
import cfme.web_ui.tabstrip as tabs
import cfme.web_ui.toolbar as tb
import utils.conf as conf


events_table = Table(
    table_locator="//div[@id='event_list_div']/fieldset/table[@class='style3']"
)
EVENT_NAME_CELL = 1

condition_folders_table = Table(
    table_locator="//div[@id='condition_folders_div']/fieldset/table[@class='style3']"
)
CONDITION_FOLDERS_CELL = 1

condition_list_table = Table(
    table_locator="//div[@id='condition_list_div']/fieldset/table[@class='style3']"
)
CONDITION_LIST_CELL = 1

actions_table = Table(
    table_locator="//div[@id='records_div']/table[@class='style3']"
)

alerts_table = Table(
    table_locator="//div[@id='records_div']/table[@class='style3']"
)

alert_profiles_main_table = Table(
    table_locator="//div[@id='alert_profile_folders_div']/fieldset/table[@class='style3']"
)

alert_profiles_list_table = Table(
    table_locator="//div[@id='alert_profile_list_div']/fieldset/table[@class='style3']"
)
ALERT_PROFILES_CELL = 1

visible_tree = Tree("//div[@class='dhxcont_global_content_area']"
                   "[not(contains(@style, 'display: none'))]/div/div/div"
                   "/ul[@class='dynatree-container']")

policies_main_table = Table(
    table_locator="//div[@id='main_div']/fieldset/table[@class='style3']"
)
POLICIES_MAIN_CELL = 1

policy_profiles_table = Table(
    table_locator="//div[@id='main_div']/fieldset/table[@class='style3']"
)
POLICY_PROFILES_CELL = 1

policies_table = Table(
    table_locator="//div[@id='records_div']/table[@class='style3']"
)


def _alert_profile_branch(ugly, nice):
    return [
        lambda _: alert_profiles_main_table.click_cell(ALERT_PROFILES_CELL,
                                                       "%s Alert Profiles" % nice),
        {
            "%s_alert_profile" % ugly:
            [
                lambda ctx: alert_profiles_list_table
                .click_cell(ALERT_PROFILES_CELL, ctx["alert_profile_name"]),
                {
                    "%s_alert_profile_edit" % ugly:
                    lambda _: tb.select("Configuration", "Edit this Alert Profile")
                }
            ],

            "%s_alert_profile_new" % ugly:
            lambda _: tb.select("Configuration", "Add a New")
        }
    ]

nav.add_branch(
    "control_explorer",
    {
        "control_explorer_policy_profiles":
        [
            lambda _: accordion.click("Policy Profiles") or
            visible_tree.click_path("All Policy Profiles"),
            {
                "policy_profile":
                lambda ctx: policy_profiles_table.click_cell(POLICY_PROFILES_CELL,
                                                             ctx["policy_profile_name"]),

                "policy_profile_new":
                lambda _: tb.select("Configuration", "Add a New Policy Profile")
            }
        ],

        "control_explorer_policies":
        [
            lambda _: accordion.click("Policies") or visible_tree.click_path("All Policies"),
            {
                "control_explorer_compliance_policies":
                [
                    lambda _: policies_main_table.click_cell(POLICIES_MAIN_CELL,
                                                             "Compliance Policies"),
                    {
                        "host_compliance_policies":
                        [
                            lambda _: policies_main_table.click_cell(POLICIES_MAIN_CELL,
                                                                     "Host Compliance Policies"),
                            {
                                "host_compliance_policy":
                                [
                                    lambda ctx: policies_table.click_cell("description",
                                                                          ctx["policy_name"]),
                                    {
                                        "host_compliance_policy_edit":
                                        lambda _: tb.select("Configuration", "Edit Basic Info"),

                                        "host_compliance_policy_events":
                                        lambda _: tb.select("Configuration", "Event assignments"),

                                        "host_compliance_policy_conditions":
                                        lambda _: tb.select("Configuration",
                                                            "Condition assignments")
                                    }
                                ],

                                "host_compliance_policy_new":
                                lambda _: tb.select("Configuration",
                                                    "Add a New Host Compliance Policy")
                            }
                        ],

                        "vm_compliance_policies":
                        [
                            lambda _: policies_main_table.click_cell(POLICIES_MAIN_CELL,
                                                                     "Vm Compliance Policies"),
                            {
                                "vm_compliance_policy":
                                [
                                    lambda ctx: policies_table.click_cell("description",
                                                                          ctx["policy_name"]),
                                    {
                                        "vm_compliance_policy_edit":
                                        lambda _: tb.select("Configuration", "Edit Basic Info"),

                                        "vm_compliance_policy_events":
                                        lambda _: tb.select("Configuration", "Event assignments"),

                                        "vm_compliance_policy_conditions":
                                        lambda _: tb.select("Configuration",
                                                            "Condition assignments")
                                    }
                                ],

                                "vm_compliance_policy_add":
                                lambda _: tb.select("Configuration",
                                                    "Add a New Vm Compliance Policy")
                            }
                        ],
                    }
                ],

                "control_explorer_control_policies":
                [
                    lambda _: policies_main_table.click_cell(POLICIES_MAIN_CELL,
                                                             "Control Policies"),
                    {
                        "host_control_policies":
                        [
                            lambda _: policies_main_table.click_cell(POLICIES_MAIN_CELL,
                                                                     "Host Control Policies"),
                            {
                                "host_control_policy":
                                [
                                    lambda ctx: policies_table.click_cell("description",
                                                                          ctx["policy_name"]),
                                    {
                                        "host_control_policy_edit":
                                        lambda _: tb.select("Configuration", "Edit Basic Info"),

                                        "host_control_policy_events":
                                        lambda _: tb.select("Configuration", "Event assignments"),

                                        "host_control_policy_conditions":
                                        lambda _: tb.select("Configuration",
                                                            "Condition assignments")
                                    }
                                ],

                                "host_control_policy_new":
                                lambda _: tb.select("Configuration",
                                                    "Add a New Host Control Policy")
                            }
                        ],

                        "vm_control_policies":
                        [
                            lambda _: policies_main_table.click_cell(POLICIES_MAIN_CELL,
                                                                     "Vm Control Policies"),
                            {
                                "vm_control_policy":
                                [
                                    lambda ctx: policies_table.click_cell("description",
                                                                          ctx["policy_name"]),
                                    {
                                        "vm_control_policy_edit":
                                        lambda _: tb.select("Configuration", "Edit Basic Info"),

                                        "vm_control_policy_events":
                                        lambda _: tb.select("Configuration", "Event assignments"),

                                        "vm_control_policy_conditions":
                                        lambda _: tb.select("Configuration",
                                                            "Condition assignments")
                                    }
                                ],

                                "vm_control_policy_new":
                                lambda _: tb.select("Configuration",
                                                    "Add a New Vm Control Policy")
                            }
                        ],
                    }
                ],
            }
        ],

        "control_explorer_events":
        [
            lambda _: accordion.click("Events") or visible_tree.click_path("All Events"),
            {
                "control_explorer_event":
                lambda ctx: events_table.click_cell(EVENT_NAME_CELL, ctx["event_name"]),
            },
        ],

        "control_explorer_conditions":
        [
            lambda _: accordion.click("Conditions") or visible_tree.click_path("All Conditions"),
            {
                "host_conditions":
                [
                    lambda _: condition_folders_table.click_cell(CONDITION_FOLDERS_CELL,
                                                                 "Host Conditions"),
                    {
                        "host_condition":
                        [
                            lambda ctx: condition_list_table.click_cell(CONDITION_LIST_CELL,
                                                                        ctx["condition_name"]),
                            {
                                "host_condition_edit":
                                lambda _: tb.select("Configuration", "Edit this Condition")
                            }
                        ],

                        "host_condition_new":
                        lambda _: tb.select("Configuration", "Add a New Host Condition")
                    }
                ],

                "vm_conditions":
                [
                    lambda _: condition_folders_table.click_cell(CONDITION_FOLDERS_CELL,
                                                                 "VM and Instance Conditions"),
                    {
                        "vm_condition":
                        [
                            lambda ctx: condition_list_table.click_cell(CONDITION_LIST_CELL,
                                                                        ctx["condition_name"]),
                            {
                                "vm_condition_edit":
                                lambda _: tb.select("Configuration", "Edit this Condition")
                            }
                        ],

                        "vm_condition_new":
                        lambda _: tb.select("Configuration", "Add a New Vm Condition")
                    }
                ]
            }
        ],

        "control_explorer_actions":
        [
            lambda _: accordion.click("Actions") or visible_tree.click_path("All Actions"),
            {
                "control_explorer_action":
                lambda ctx: actions_table.click_cell("description", ctx["action_name"]),
            },
        ],

        "control_explorer_alert_profiles":
        [
            lambda _: accordion.click("Alert Profiles")
            or visible_tree.click_path("All Alert Profiles"),
            {
                "cluster_alert_profiles":
                _alert_profile_branch("cluster", "Cluster"),

                "datastore_alert_profiles":
                _alert_profile_branch("datastore", "Datastore"),

                "host_alert_profiles":
                _alert_profile_branch("host", "Host"),

                "provider_alert_profiles":
                _alert_profile_branch("provider", "Provider"),

                "server_alert_profiles":
                _alert_profile_branch("server", "Server"),

                "vm_instance_alert_profiles":
                _alert_profile_branch("vm_instance", "VM and Instance"),
            }
        ],

        "control_explorer_alerts":
        [
            lambda _: accordion.click("Alerts") or visible_tree.click_path("All Alerts"),
            {
                "control_explorer_alert":
                [
                    lambda ctx: alerts_table.click_cell("description", ctx["alert_name"]),
                    {
                        "control_explorer_alert_edit":
                        lambda ctx: tb.select("Configuration", "Edit this Alert")
                    },
                ],

                "control_explorer_alert_new":
                lambda _: tb.select("Configuration", "Add a New Alert"),
            }
        ],
    }
)


###################################################################################################
# For checking whether passed condition can be assigned to the policy, some class stuff comes here.
###################################################################################################
class _type_check_object(object):
    """ This class is used to check, whether one object can be assigned to another

    """
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
    """ Base class for conditions.

    They differ just with the navigation prefix, so that is the self.PREFIX which gets changed.

    Usage:

        >>> cond = HostCondition("mycond",         # or VMCondition
        ...     expression="fill_count(Host.VMs, >, 50)",
        ...     scope="fill_count(Host.Files, >, 150)")
        >>> cond.create()
        >>> cond.update(notes="Important!")
        >>> cond.delete()

    Args:
        description: Name of the condition.
        notes: Notes
        scope: Program, setting the Scope of the Condition.
        expression: Program, setting the Scope of the Expression.
    """
    PREFIX = None

    buttons = Region(
        locators=dict(
            add="//div[@id='buttons_on']//img[@alt='Add']",
            cancel="//div[@id='buttons_on']//img[@alt='Cancel']",
            save="//div[@id='buttons_on']//img[@alt='Save Changes']",
            reset="//div[@id='buttons_on']//img[@alt='Reset Changes']",
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
        self.scope = editor.create_program(scope)
        self.expression = editor.create_program(expression)

    def _do_expression_editing(self):
        """ Fills the expression fields using the mini-programs.

        It handles switching between Scope and Expression editor.
        """
        if self.scope is not None:
            if not self.is_editing_scope:
                browser.click(self.buttons.edit_scope)
            self.scope()
        if self.expression is not None:
            if not self.is_editing_expression:
                browser.click(self.buttons.edit_expression)
            self.expression()

    def create(self, cancel=False):
        """ Creates new Condition according to the informations filed in constructor

        Args:
            cancel: Whether to cancel the process instead of saving.
        """
        browser.force_navigate(self.PREFIX + "condition_new")
        self._do_expression_editing()
        action = self.buttons.cancel if cancel else self.buttons.add
        return fill(self.form, dict(description=self.description, notes=self.notes), action=action)

    def update(self, description=None, notes=None, scope=None, expression=None, cancel=False):
        """ Updates the informations in the object and then updates the Condition in CFME

        Args:
            description, notes, scope, expression: See constructor
            cancel: Whether to cancel the process instead of saving.
        """
        browser.force_navigate(self.PREFIX + "condition_edit",
                               context=dict(condition_name=self.description))
        if description is not None:
            self.description = description
        if notes is not None:
            self.notes = notes
        if scope is not None:
            self.scope = editor.create_program(scope)
        if expression is not None:
            self.expression = editor.create_program(expression)
        if scope is not None or expression is not None:
            self._do_expression_editing()
        action = self.buttons.cancel if cancel else self.buttons.save
        return fill(self.form, dict(description=self.description, notes=self.notes), action=action)

    def delete(self, cancel=False):
        """ Deletes the condition in CFME

        Args:
            cancel: Whether to cancel the process instead of saving.
        """
        browser.force_navigate(self.PREFIX + "condition",
                               context=dict(condition_name=self.description))
        tb.select("Configuration", "Delete this", invokes_alert=True)
        browser.handle_alert(cancel)

    @property
    def is_editing_scope(self):
        """ Is editor for Scope displayed?

        Returns: :py:class:`bool`
        """
        self._wait_form_displayed()
        return browser.is_displayed(self.buttons.edit_expression)

    @property
    def is_editing_expression(self):
        """ Is editor for Expression displayed?

        Returns: :py:class:`bool`
        """
        self._wait_form_displayed()
        return browser.is_displayed(self.buttons.edit_scope)

    def _wait_form_displayed(self):
        """ The buttons for choosing Scope or Expression appear a bit later, so we have to wait.
        """
        return browser.wait_for_element(self.buttons.edit_scope, self.buttons.edit_expression)


class VMCondition(BaseCondition, VMObject):
    PREFIX = "vm_"


class HostCondition(BaseCondition, HostObject):
    PREFIX = "host_"


class BasePolicy(Updateable):
    PREFIX = None

    buttons = Region(
        locators=dict(
            add="//div[@id='buttons_on']//img[@alt='Add']",
            cancel="//div[@id='buttons_on']//img[@alt='Cancel']",
            save="//div[@id='buttons_on']//img[@alt='Save Changes']",
            reset="//div[@id='buttons_on']//img[@alt='Reset Changes']",
        )
    )

    form = Form(
        fields=[
            ("description", "//input[@id='description']"),
            ("active", "//input[@id='active']"),
            ("notes", "//textarea[@id='notes']"),
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
        self.scope = editor.create_program(scope)

    def create(self, cancel=False):
        """ Creates new Condition according to the informations filed in constructor

        Args:
            cancel: Whether to cancel the process instead of saving.
        """
        browser.force_navigate(self.PREFIX + "policy_new")
        if self.scope is not None:
            self.scope()
        action = self.buttons.cancel if cancel else self.buttons.add
        return fill(
            self.form,
            dict(
                description=self.description,
                notes=self.notes,
                active=self.active
            ),
            action=action)

    def update(self, description=None, active=True, notes=None, scope=None, cancel=False):
        """ Updates the informations in the object and then updates the Condition in CFME

        Args:
            description, active, notes, scope: See constructor
            cancel: Whether to cancel the process instead of saving.
        """
        browser.force_navigate(self.PREFIX + "policy_edit",
                               context=dict(policy_name=self.description))
        if description is not None:
            self.description = description
        if notes is not None:
            self.notes = notes
        if scope is not None:
            self.scope = editor.create_program(scope)
            self.scope()
        action = self.buttons.cancel if cancel else self.buttons.save
        return fill(
            self.form,
            dict(
                description=self.description,
                notes=self.notes,
                active=self.active
            ),
            action=action)

    def delete(self, cancel=False):
        """ Deletes the condition in CFME

        Args:
            cancel: Whether to cancel the process instead of saving.
        """
        browser.force_navigate(self.PREFIX + "policy", context=dict(policy_name=self.description))
        tb.select("Configuration", "Delete this", invokes_alert=True)
        browser.handle_alert(cancel)

    def assign_conditions(self, *conditions):
        """ Assign one or more conditions to this Policy.

        If using the :py:class:`BaseCondition` assignment, you must provide a correct type of
        condition (you cannot assign eg. :py:class:`VMCondition` to :py:class:`HostControlPolicy`)

        Args:
            *conditions: Each condition can be either :py:class:`str` or :py:class:`BaseCondition`
                instance
        """
        browser.force_navigate(self.PREFIX + "policy_conditions",
                               context=dict(policy_name=self.description))
        for condition in conditions:
            assign_name = None
            if isinstance(condition, BaseCondition):
                if not self._is_assignable(condition):
                    raise TypeError("You cannot add VM object to Host and vice versa!")
                # Assign condition.description
                logger.debug(
                    "Assigning condition `%s` to policy `%s`" % (condition.description,
                                                                 self.description))
                assign_name = condition.description
            elif isinstance(condition, basestring):
                # assign condition
                logger.debug(
                    "Assigning condition `%s` to policy `%s`" % (condition,
                                                                 self.description))
                assign_name = condition
            else:
                raise TypeError("assign_conditions() accepts only BaseCondition and basestring")
        raise NotImplementedError("This has to be implemented!")


class BaseControlPolicy(BasePolicy):
    def assign_events(self, *events, **kwargs):
        """ (un)Assign one or more events to this Policy.

        Args:
            *events: Each event is represented by :py:class:`str`. If it is present, it will be
                checked. If it is not present, it will be unchecked
        Keywords:
            do_not_uncheck: If specified and True, no unchecking will happen.
        """
        browser.force_navigate(self.PREFIX + "policy_events",
                               context=dict(policy_name=self.description))
        event_ids = {}
        # Create event mapping
        for event_cb in browser.elements("//input[@type='checkbox'][contains(@id, 'event_')]"):
            desc = event_cb.find_element_by_xpath("..").text.encode("utf-8")
            event_ids[desc] = event_cb.get_attribute("id")
        # Create dictionary to pass to the checker func (could be merged with code above though)
        check_dict = {}
        normalized_events = set([normalize_text(event) for event in events])
        for desc, id in event_ids.iteritems():
            if normalize_text(desc) in normalized_events:
                check_dict[(By.ID, id)] = True
            elif not kwargs.get("do_not_uncheck", False):
                check_dict[(By.ID, id)] = False
        browser.multi_check(check_dict)
        browser.click(self.buttons.save)


class HostCompliancePolicy(BasePolicy, HostObject):
    PREFIX = "host_compliance_"


class VMCompliancePolicy(BasePolicy, VMObject):
    PREFIX = "vm_compliance_"


class HostControlPolicy(BaseControlPolicy, HostObject):
    PREFIX = "host_control_"


class VMControlPolicy(BaseControlPolicy, VMObject):
    PREFIX = "vm_control_"


class Alert(Updateable):
    """ Alarm representation object.

    Args:
        description: Name of the Alert
        based_on: Cluster, Datastore, Host, Provider, ...
        evaluate: If specified as :py:class:`str`, it will select 'Expression (Custom)' and compile
            the string into the program which selects the expression. If specified as callable
            (something that has `.__call__` method inside), then it will also select the custom
            expression and will use the function to fill the expression. If specified as tuple(list)
            it will use it as follows: `("What to Evaluate selection", dict(values="for form")).
            If you want to select Nothing, you will therefore pass ("Nothing", {}).

            Other example:
                ("Hardware Reconfigured",
                 dict(hw_attribute="Number of CPUs", hw_attribute_operator="Increased")
                )

            For all fields, check the `form` class variable.
        driving_event: This Alert's driving event (Hourly Timer, ...)
        notification_frequency: 1 Minute, 2 Minutes, ...
        snmp_trap: Whether to raise SNMP trap (reveals another part of form)
        snmp_trap_hosts: :py:class:`list` of hosts (max 3) for SNMP trap (depends on snmp_trap!)
        snmp_trap_version: v1 or v2 (depends on snmp_trap!)
        snmp_trap_number: SNMP trap number (depends on snmp_trap!)
        snmp_objects: :py:class:`list` of 2- or 3-tuples in format (oid, type[, value])
            (depends on snmp_trap!)
        timeline_event: Whether generate a timeline event
        mgmt_event: Whether to send a Management Event (reveals another part of form)
        mgmt_event_name:  Management Event's name (depends on mgmt_event!)

    Note:
        If you don't specify the 'master' option or set it False (like snmp_trap for
        snmp_trap_hosts), the dependent variables will be None'd to ensure that things like
        :py:class:`NoSuchElementException` do not happen.


    """
    buttons = Region(
        locators=dict(
            add="//div[@id='buttons_on']//img[@alt='Add']",
            cancel="//div[@id='buttons_on']//img[@alt='Cancel']",
            save="//div[@id='buttons_on']//img[@alt='Save Changes']",
            reset="//div[@id='buttons_on']//img[@alt='Reset Changes']",
        )
    )

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
            ("based_on", "//select[@id='miq_alert_db']"),
            ("evaluate", "//select[@id='exp_name']"),
            ("driving_event", "//select[@id='exp_event']"),
            ("based_on", "//select[@id='miq_alert_db']"),
            ("notification_time", "//select[@id='repeat_time']"),
            # Different evaluations begin
            # Event log threshold
            ("event_log_message_type", "//select[@id='select_event_log_message_filter_type']"),
            ("event_log_message_value", "//input[@id='event_log_message_filter_value']"),
            ("event_log_name", "//input[@id='event_log_name']"),
            ("event_log_level", "//input[@id='event_log_level']"),
            ("event_log_event_id", "//input[@id='event_log_event_id']"),
            ("event_log_source", "//input[@id='event_log_source']"),
            ("event_time_threshold", "//select[@id='time_threshold']"),  # shared
            ("event_count_threshold", "//input[@id='freq_threshold']"),  # shared
            # Event threshold (uses the shared fields from preceeding section)
            ("event_type", "//select[@id='event_types']"),
            # HW reconfigured + VM Value Changed
            ("hw_attribute", "//select[@id='select_hdw_attr']"),
            ("hw_attribute_operator", "//select[@id='select_operator']"),
            # Normal operating range
            ("performance_field", "//select[@id='perf_column']"),
            ("performance_field_operator", "//select[@id='select_operator']"),
            ("performance_time_threshold", "//select[@id='rt_time_threshold']"),
            # Real Time Performance (uses fields from previous)
            ("performance_field_value", "//input[@id='value_threshold']"),
            ("performance_trend", "//select[@id='trend_direction']"),
            ("performance_debug_trace", "//select[@id='debug_trace']"),
            # VMWare alarm
            ("vmware_alarm_provider", "//select[@id='select_ems_id']"),
            ("vmware_alarm_type", "//select[@id='select_ems_alarm_mor']"),
            # Different evaluations end
            ("send_email", "//input[@id='send_email_cb']"),
            ("send_email", "//input[@id='send_email_cb']"),
            ("send_email_from", "//input[@id='from']"),
            ("send_email_to", "//select[@id='user_email']"),
            ("snmp_trap", "//input[@id='send_snmp_cb']"),
            ("snmp_trap_host_1", "//input[@id='host_1']"),
            ("snmp_trap_host_2", "//input[@id='host_2']"),
            ("snmp_trap_host_3", "//input[@id='host_3']"),
            ("snmp_trap_version", "//select[@id='snmp_version']"),
            ("snmp_trap_number", "//input[@id='trap_id']"),
            ("snmp_trap_oid_1", "//input[@id='oid__1']"),
            ("snmp_trap_oid_2", "//input[@id='oid__2']"),
            ("snmp_trap_oid_3", "//input[@id='oid__3']"),
            ("snmp_trap_oid_4", "//input[@id='oid__4']"),
            ("snmp_trap_oid_5", "//input[@id='oid__5']"),
            ("snmp_trap_oid_6", "//input[@id='oid__6']"),
            ("snmp_trap_oid_7", "//input[@id='oid__7']"),
            ("snmp_trap_oid_8", "//input[@id='oid__8']"),
            ("snmp_trap_oid_9", "//input[@id='oid__9']"),
            ("snmp_trap_oid_10", "//input[@id='oid__10']"),
            ("snmp_trap_type_1", "//input[@id='var_type__1']"),
            ("snmp_trap_type_2", "//input[@id='var_type__2']"),
            ("snmp_trap_type_3", "//input[@id='var_type__3']"),
            ("snmp_trap_type_4", "//input[@id='var_type__4']"),
            ("snmp_trap_type_5", "//input[@id='var_type__5']"),
            ("snmp_trap_type_6", "//input[@id='var_type__6']"),
            ("snmp_trap_type_7", "//input[@id='var_type__7']"),
            ("snmp_trap_type_8", "//input[@id='var_type__8']"),
            ("snmp_trap_type_9", "//input[@id='var_type__9']"),
            ("snmp_trap_type_10", "//input[@id='var_type__10']"),
            ("snmp_trap_value_1", "//input[@id='value__1']"),
            ("snmp_trap_value_2", "//input[@id='value__2']"),
            ("snmp_trap_value_3", "//input[@id='value__3']"),
            ("snmp_trap_value_4", "//input[@id='value__4']"),
            ("snmp_trap_value_5", "//input[@id='value__5']"),
            ("snmp_trap_value_6", "//input[@id='value__6']"),
            ("snmp_trap_value_7", "//input[@id='value__7']"),
            ("snmp_trap_value_8", "//input[@id='value__8']"),
            ("snmp_trap_value_9", "//input[@id='value__9']"),
            ("snmp_trap_value_10", "//input[@id='value__10']"),
            ("timeline_event", "//input[@id='send_evm_event_cb']"),
            ("mgmt_event", "//input[@id='send_event_cb']"),
            ("mgmt_event_name", "//input[@id='event_name']"),
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
                 snmp_trap_hosts=None,
                 snmp_trap_version=None,
                 snmp_trap_number=None,
                 snmp_objects=None,
                 timeline_event=None,
                 mgmt_event=None,
                 mgmt_event_name=None):
        for key, value in locals().iteritems():
            if key == "self":
                continue
            setattr(self, key, value)

    def create(self, cancel=False):
        browser.force_navigate("control_explorer_alert_new")
        self._fix_dependencies()
        self._fill()
        if cancel:
            browser.click(self.buttons.cancel)
        else:
            browser.click(self.buttons.add)

    def update(self,
               description=None,
               active=None,
               based_on=None,
               evaluate=None,
               driving_event=None,
               notification_frequency=None,
               snmp_trap=None,
               snmp_trap_hosts=None,
               snmp_trap_version=None,
               snmp_trap_number=None,
               snmp_objects=None,
               timeline_event=None,
               mgmt_event=None,
               mgmt_event_name=None,
               cancel=False):
        """ Update the object with new values and save

        Args:
            cancel: Whether to cancel the update (default False)
        """
        for key, value in locals().iteritems():
            if key in {"self", "cancel"}:
                continue
            try:
                getattr(self, key)
                if value is not None:
                    setattr(self, key, value)
            except AttributeError:
                pass
        # Go update!
        browser.force_navigate("control_explorer_alert_edit",
                               context={"alert_name": self.description})
        self._fix_dependencies()
        self._fill()
        if cancel:
            browser.click(self.buttons.cancel)
        else:
            browser.click(self.buttons.save)

    def delete(self, cancel=False):
        """ Delete this Alert from CFME

        Args:
            cancel: Whether to cancel the deletion (default False)
        """
        browser.force_navigate("control_explorer_alert", context={"alert_name": self.description})
        tb.select("Configuration", "Delete this Alert", invokes_alert=True)
        browser.handle_alert(cancel)

    def _fix_dependencies(self):
        """ This function 'Nones' all child choices of the mgmt_event and snmp_trap.
        """
        if self.mgmt_event is False:
            self.mgmt_event_name = None
        if self.snmp_trap is False:
            for item in [x for x in dir(self) if x.startswith("snmp_trap_")]:
                setattr(self, item, None)

    def _fill(self):
        """ This function prepares the values and fills the form.
        """
        fill_details = dict(
            description=self.description,
            active=self.active,
            based_on=self.based_on,
            driving_event=self.driving_event,
            notification_frequency=self.notification_frequency,
            snmp_trap=self.snmp_trap,
            snmp_trap_version=self.snmp_trap_version,
            snmp_trap_number=self.snmp_trap_number,
            timeline_event=self.timeline_event,
            mgmt_event=self.mgmt_event,
            mgmt_event_name=self.mgmt_event_name
        )
        # evaluate and snmp hosts and objects missing
        form_func = lambda: None
        if self.snmp_trap_hosts:
            for i, host in enumerate(self.snmp_trap_hosts):
                fill_details["snmp_trap_host_%d" % (i + 1)] = host
        if self.snmp_objects:
            for i, obj in enumerate(self.snmp_objects):
                assert 2 <= len(obj) <= 3, "SNMP object must be 2- or 3-tuple"
                fill_details["snmp_trap_oid_%d" % (i + 1)] = obj[0]
                fill_details["snmp_trap_type_%d" % (i + 1)] = obj[1]
                if len(obj) == 3:
                    fill_details["snmp_trap_value_%d" % (i + 1)] = obj[2]
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
    def __init__(self):
        pass
