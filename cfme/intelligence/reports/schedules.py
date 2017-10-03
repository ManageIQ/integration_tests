# -*- coding: utf-8 -*-
"""Module handling schedules"""
import attr

from navmazing import NavigateToSibling, NavigateToAttribute

from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import Text, Checkbox, TextInput
from widgetastic_manageiq import Calendar, AlertEmail, Table, PaginationPane
from widgetastic_patternfly import Button, BootstrapSelect

from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.update import Updateable
from cfme.utils.pretty import Pretty

from . import CloudIntelReportsView


class SchedulesAllView(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    schedules_table = Table(".//div[@id='records_div']/table")
    paginator = PaginationPane()

    @property
    def is_displayed(self):
        return self.in_intel_reports and self.title.text == "All Schedules"


class SchedulesFormCommon(CloudIntelReportsView):
    # Basic Information
    title = Text("#explorer_title_text")
    name = TextInput(name="name")
    description = TextInput(name="description")
    active = Checkbox("enabled")
    # Report Selection
    filter1 = BootstrapSelect("filter_typ")
    filter2 = BootstrapSelect("subfilter_typ")
    filter3 = BootstrapSelect("repfilter_typ")
    # Timer
    run = BootstrapSelect("timer_typ")
    time_zone = BootstrapSelect("time_zone")
    starting_date = Calendar("miq_date_1")
    hour = BootstrapSelect("start_hour")
    minute = BootstrapSelect("start_min")
    # Email
    emails_send = Checkbox("send_email_cb")
    emails = AlertEmail()
    send_if_empty = Checkbox("send_if_empty")
    send_txt = Checkbox("send_txt")
    send_csv = Checkbox("send_csv")
    send_pdf = Checkbox("send_pdf")
    # Buttons
    cancel_button = Button("Cancel")


class NewScheduleView(SchedulesFormCommon):
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == "Adding a new Schedule" and
            # TODO uncomment when https://bugzilla.redhat.com/show_bug.cgi?id=1441101 will be fixed
            # self.schedules.is_opened and
            self.schedules.tree.currently_selected == ["All Schedules"]
        )


class EditScheduleView(SchedulesFormCommon):
    save_button = Button("Save")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == 'Editing Schedule "{}"'.format(self.context["object"].name) and
            # TODO uncomment when https://bugzilla.redhat.com/show_bug.cgi?id=1441101 will be fixed
            # self.schedules.is_opened and
            self.schedules.tree.currently_selected == ["All Schedules", self.context["object"].name]
        )


class ScheduleDetailsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == 'Schedule "{}"'.format(self.context["object"].name) and
            # TODO uncomment when https://bugzilla.redhat.com/show_bug.cgi?id=1441101 will be fixed
            # self.schedules.is_opened and
            self.schedules.tree.currently_selected == ["All Schedules", self.context["object"].name]
        )


@attr.s
class Schedule(Updateable, Pretty, BaseEntity):
    """Represents a schedule in Cloud Intel/Reports/Schedules.

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
    pretty_attrs = ["name", "filter"]

    def __str__(self):
        return self.name

    name = attr.ib()
    description = attr.ib()
    filter = attr.ib()
    active = attr.ib(default=None)
    timer = attr.ib(default=None)
    emails = attr.ib(default=None)
    email_options = attr.ib(default=None)

    @property
    def exists(self):
        schedules = self.appliance.db["miq_schedules"]
        return self.appliance.db.session\
            .query(schedules.name)\
            .filter(schedules.name == self.name)\
            .count() > 0

    def update(self, updates):
        view = navigate_to(self, "Edit")
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(ScheduleDetailsView, override=updates)
        assert view.is_displayed
        # TODO Doesn't work due https://bugzilla.redhat.com/show_bug.cgi?id=1441101
        # view.flash.assert_no_error()
        # if changed:
        #     view.flash.assert_message(
        #         'Schedule "{}" was saved'.format(updates.get("name", self.name)))
        # else:
        #     view.flash.assert_message(
        #         'Edit of Schedule "{}" was cancelled by the user'.format(self.name))

    def delete(self, cancel=False):
        view = navigate_to(self, "Details")
        view.configuration.item_select("Delete this Schedule", handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
        else:
            view = self.create_view(SchedulesAllView)
            assert view.is_displayed
        # TODO Doesn't work due https://bugzilla.redhat.com/show_bug.cgi?id=1441101
        # view.flash.assert_no_error()

    def queue(self):
        """Queue this schedule."""
        view = navigate_to(self, "Details")
        view.configuration.item_select("Queue up this Schedule to run now")


@attr.s
class ScheduleCollection(BaseCollection):

    ENTITY = Schedule

    def create(self, name=None, description=None, filter=None, active=None,
               timer=None, emails=None, email_options=None):
        schedule = self.instantiate(name, description, filter, active=active, timer=timer,
            emails=emails, email_options=email_options)
        view = navigate_to(self, "Add")
        view.fill({
            "name": name,
            "description": description,
            "active": active,
            "filter1": filter[0],
            "filter2": filter[1],
            "filter3": filter[2],
            "run": timer.get("run"),
            "time_zone": timer.get("time_zone"),
            "starting_date": timer.get("starting_date"),
            "hour": timer.get("hour"),
            "minute": timer.get("minute"),
            "emails_send": bool(emails),
            "emails": emails,
            "send_if_empty": email_options.get("send_if_empty"),
            "send_txt": email_options.get("send_txt"),
            "send_csv": email_options.get("send_csv"),
            "send_pdf": email_options.get("send_pdf")
        })
        view.add_button.click()
        view = schedule.create_view(ScheduleDetailsView)
        assert view.is_displayed
        # TODO Doesn't work due https://bugzilla.redhat.com/show_bug.cgi?id=1441101
        # view.flash.assert_success_message('Schedule "{}" was added'.format(name))
        return schedule

    def _select_schedules(self, schedules):
        """Select schedules in the table.

        Args:
            schedules: Schedules to select.
        Raises: :py:class:`NameError` when some of the schedules were not found.
        """
        view = navigate_to(self, "All")
        failed_selections = []
        try:
            for schedule in schedules:
                name = str(schedule)
                cell = view.table.row(name=name)[0]
                cell.check()
        except NoSuchElementException:
            failed_selections.append(name)
        if failed_selections:
            raise NameError("These schedules were not found: {}.".format(
                ", ".join(failed_selections)
            ))
        return view

    def _action_on_schedules(self, action, schedules, cancel=False):
        """Select schedules and perform an action on them

        Args:
            action: Action in Configuration to perform.
            schedules: List of schedules.
            cancel: If specified, the nalert is expected after clicking on action and value of the
                variable specifies handling behaviour.
        Raises: :py:class:`NameError` when some of the schedules were not found.
        """
        view = self._select_schedules(schedules)
        view.configuration.item_select(action, handle_alert=not cancel)
        # TODO https://bugzilla.redhat.com/show_bug.cgi?id=1441101
        # view.flash.assert_no_errors()

    def enable_schedules(self, *schedules):
        """Select and enable specified schedules.

        Args:
            *schedules: Schedules to enable. Can be objects or strings.
        Raises: :py:class:`NameError` when some of the schedules were not found.
        """
        self._action_on_schedules("Enable the selected Schedules", schedules)

    def disable_schedules(self, *schedules):
        """Select and disable specified schedules.

        Args:
            *schedules: Schedules to disable. Can be objects or strings.
        Raises: :py:class:`NameError` when some of the schedules were not found.
        """
        self._action_on_schedules("Disable the selected Schedules", schedules)

    def queue_schedules(self, *schedules):
        """Select and queue specified schedules.

        Args:
            *schedules: Schedules to queue. Can be objects or strings.
        Raises: :py:class:`NameError` when some of the schedules were not found.
        """
        self._action_on_schedules("Queue up selected Schedules to run now", schedules)

    def delete_schedules(self, *schedules, **kwargs):
        """Select and delete specified schedules from VMDB.

        Args:
            *schedules: Schedules to delete. Can be objects or strings.
            cancel: (kwarg) Whether to cancel the deletion (Default: False)
        Raises: :py:class:`NameError` when some of the schedules were not found.
        """
        self._action_on_schedules(
            "Delete the selected Schedules", schedules, kwargs.pop("cancel", False)
        )


@navigator.register(ScheduleCollection, "All")
class ScheduleAll(CFMENavigateStep):
    VIEW = SchedulesAllView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.prerequisite_view.schedules.tree.click_path("All Schedules")


@navigator.register(ScheduleCollection, "Add")
class ScheduleNew(CFMENavigateStep):
    VIEW = NewScheduleView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.view.configuration.item_select("Add a new Schedule")


@navigator.register(Schedule, "Details")
class ScheduleDetails(CFMENavigateStep):
    VIEW = ScheduleDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.prerequisite_view.schedules.tree.click_path("All Schedules", self.obj.name)


@navigator.register(Schedule, "Edit")
class ScheduleEdit(CFMENavigateStep):
    VIEW = EditScheduleView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.configuration.item_select("Edit this Schedule")
