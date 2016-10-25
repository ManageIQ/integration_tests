# -*- coding: utf-8 -*-
"""Module handling schedules"""
from functools import partial

from cfme.fixtures import pytest_selenium as sel
from cfme.intelligence.reports.ui_elements import Timer
from cfme.web_ui import (EmailSelectForm, Form, CheckboxTable, Select, ShowingInputs, accordion,
    fill, flash, toolbar, form_buttons, Input)
from cfme.web_ui.menu import nav
from utils.db import cfmedb
from utils.update import Updateable
from utils.wait import wait_for
from utils.pretty import Pretty
from utils import version


cfg_btn = partial(toolbar.select, "Configuration")


schedules_table = CheckboxTable("//div[@id='records_div']//table[thead]")


def get_sch_name(sch):
    """Enables us using both string and schedule object"""
    if isinstance(sch, basestring):
        return sch
    elif isinstance(sch, Schedule):
        return sch.name
    else:
        return str(sch)

nav.add_branch(
    "reports",
    {
        "schedules":
        [
            lambda ctx: accordion.tree("Schedules", "All Schedules"),
            {
                "schedule_add": lambda ctx: cfg_btn("Add a new Schedule")
            }
        ],

        "schedule":
        [
            lambda ctx: accordion.tree("Schedules", "All Schedules", get_sch_name(ctx["schedule"])),
            {
                "schedule_edit": lambda ctx: cfg_btn("Edit this Schedule")
            }
        ],
    }
)


class Schedule(Updateable, Pretty):
    """Represents a schedule in Intelligence/Reports/Schedules.

    Args:
        name: Schedule name.
        description: Schedule description.
        filter: 3-tuple with filter selection (see the UI).
        active: Whether is this schedule active.
        run: Specifies how often this schedule runs. It can be either string "Once", or a tuple,
            which maps to the two selects in UI ("Hourly", "Every hour")...
        time_zone: Specify time zone.
        start_date: Specify the start date.
        start_time: Specify the start time either as a string ("0:15") or tuple ("0", "15")
        send_email: If specifies, turns on e-mail sending. Can be string, or list or set.
    """
    form = Form(fields=[
        ("name", Input("name")),
        ("description", Input("description")),
        ("active", Input("enabled")),
        ("filter", ShowingInputs(
            Select("//select[@id='filter_typ']"),
            Select("//select[@id='subfilter_typ']"),
            Select("//select[@id='repfilter_typ']"),
            min_values=3
        )),
        ("timer", Timer()),
        ("send_email", Input("send_email_cb")),
        ("emails", EmailSelectForm())
    ])

    _run_mapping = {
        "Once": None,
        "Hourly": "run_hours",
        "Daily": "run_days",
        "Weekly": "run_weekly",
        "Monthly": "run_months"
    }

    pretty_attrs = ['name', 'filter']

    def __init__(
            self,
            name,
            description,
            filter,
            active=None,
            timer=None,
            send_email=None):
        self.name = name
        self.description = description
        self.filter = filter
        self.active = active
        self.timer = timer
        self.send_email = send_email

    @property
    def exists(self):
        schedules = cfmedb()["miq_schedules"]
        return cfmedb().session\
            .query(schedules.name)\
            .filter(schedules.name == self.name)\
            .count() > 0

    def _fill(self, action):
        fill(
            self.form,
            self._create_fill_dict(),
            action=action
        )

    def create(self, cancel=False):
        sel.force_navigate("schedule_add")
        self._fill(form_buttons.add if not cancel else form_buttons.cancel)
        flash.assert_no_errors()
        assert self.exists, "Schedule does not exist!"

    def update(self, updates):
        sel.force_navigate("schedule_edit", context={"schedule": self})
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()
        assert self.exists, "Schedule does not exist!"

    def delete(self, cancel=False):
        sel.force_navigate("schedule", context={"schedule": self})
        delete_label = version.pick({
            "5.6": "Delete this Schedule from the VMDB",
            "5.7": "Delete this Schedule"})
        cfg_btn(delete_label, invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()
        assert not self.exists, "Schedule does not exist!"

    def table_item(self, item):
        """Works both up- and downstream.

        I think this should be incorporated into InfoBlock somehow. Currently there is the fieldset
        issue.
        """
        return (
            version.pick({
                version.LOWEST: "//td[preceding-sibling::td[contains(@class, 'key')"
                                " and normalize-space(.)='{}']]",
                         "5.5": "//label[contains(@class, 'control-label')"
                                " and normalize-space(.)='{}']/../div/p"}).format(item)
        )

    def queue(self, wait_for_finish=False):
        """Queue this schedule.

        Args:
            wait_for_finish: If True, then this function blocks until the action is finished.
        """
        if not self.exists:
            self.create()
        sel.force_navigate("schedule", context={"schedule": self})
        last_run = sel.text(self.table_item("Last Run Time")).strip()
        cfg_btn("Queue up this Schedule to run now")
        flash.assert_no_errors()
        if wait_for_finish:
            wait_for(
                lambda: sel.text(self.table_item("Last Run Time")).strip() != last_run,
                delay=2,
                fail_func=lambda: toolbar.select("Reload current display"),
                message="wait for report queue finish"
            )

    def _create_fill_dict(self):
        """Handle the values, create dictionary for form"""
        # Simple values come
        fields = {
            "name": self.name,
            "description": self.description,
            "active": self.active,
            "filter": self.filter,
            "timer": self.timer,
        }

        # Send e-mail
        if self.send_email is not None:
            fields["send_email"] = True
            fields["emails"] = self.send_email

        return fields

    # Methods for all schedules
    @classmethod
    def _select_schedules(cls, schedules):
        """Select schedules in the table.

        Args:
            schedules: Schedules to select.
        Raises: :py:class:`NameError` when some of the schedules were not found.
        """
        sel.force_navigate("schedules")
        failed_selections = []
        for schedule in schedules:
            if isinstance(schedule, cls):
                name = schedule.name
            else:
                name = str(schedule)
            if not schedules_table.select_row("Name", name):
                failed_selections.append(name)
        if failed_selections:
            raise NameError("These schedules were not found: {}.".format(
                ", ".join(failed_selections)
            ))

    @classmethod
    def _action_on_schedules(cls, action, schedules, cancel=None):
        """Select schedules and perform an action on them

        Args:
            action: Action in Configuration to perform.
            schedules: List of schedules.
            cancel: If specified, the nalert is expected after clicking on action and value of the
                variable specifies handling behaviour.
        Raises: :py:class:`NameError` when some of the schedules were not found.
        """
        cls._select_schedules(schedules)
        if cancel is None:
            cfg_btn(action)
        else:
            cfg_btn(action, invokes_alert=True)
            sel.handle_alert(bool(cancel))
        flash.assert_no_errors()

    @classmethod
    def enable_schedules(cls, *schedules):
        """Select and enable specified schedules.

        Args:
            *schedules: Schedules to enable. Can be objects or strings.
        Raises: :py:class:`NameError` when some of the schedules were not found.
        """
        return cls._action_on_schedules("Enable the selected Schedules", schedules)

    @classmethod
    def disable_schedules(cls, *schedules):
        """Select and disable specified schedules.

        Args:
            *schedules: Schedules to disable. Can be objects or strings.
        Raises: :py:class:`NameError` when some of the schedules were not found.
        """
        return cls._action_on_schedules("Disable the selected Schedules", schedules)

    @classmethod
    def queue_schedules(cls, *schedules):
        """Select and queue specified schedules.

        Args:
            *schedules: Schedules to queue. Can be objects or strings.
        Raises: :py:class:`NameError` when some of the schedules were not found.
        """
        return cls._action_on_schedules("Queue up selected Schedules to run now", schedules)

    @classmethod
    def delete_schedules(cls, *schedules, **kwargs):
        """Select and delete specified schedules from VMDB.

        Args:
            *schedules: Schedules to delete. Can be objects or strings.
            cancel: (kwarg) Whether to cancel the deletion (Default: False)
        Raises: :py:class:`NameError` when some of the schedules were not found.
        """
        return cls._action_on_schedules(
            "Delete the selected Schedules from the VMDB", schedules, kwargs.get("cancel", False)
        )
