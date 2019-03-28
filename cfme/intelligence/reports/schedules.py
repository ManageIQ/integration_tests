# -*- coding: utf-8 -*-
"""Module handling schedules"""
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import Checkbox
from widgetastic.widget import Text
from widgetastic.widget import TextInput
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import FlashMessages

from . import CloudIntelReportsView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from widgetastic_manageiq import AlertEmail
from widgetastic_manageiq import Calendar
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import Table


class SchedulesAllView(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    schedules_table = Table(".//div[@id='records_div' or @id='main_div']//table")
    paginator = PaginationPane()

    @property
    def is_displayed(self):
        return self.in_intel_reports and self.title.text == "All Schedules"


# TODO debug the closing widget behavior
class BootstrapSelectRetry(BootstrapSelect):
    """Workaround for schedule filter widget that is closing itself

    Retrys the open action
    """
    def open(self):
        super(BootstrapSelectRetry, self).open()
        if not self.is_open:
            super(BootstrapSelectRetry, self).open()


class SchedulesFormCommon(CloudIntelReportsView):
    flash = FlashMessages('.//div[@id="flash_msg_div"]')
    # Basic Information
    title = Text("#explorer_title_text")
    name = TextInput(name="name")
    description = TextInput(name="description")
    active = Checkbox("enabled")
    # Report Selection
    filter1 = BootstrapSelectRetry("filter_typ")
    filter2 = BootstrapSelectRetry("subfilter_typ")
    filter3 = BootstrapSelectRetry("repfilter_typ")
    # Timer
    run = BootstrapSelect("timer_typ")
    # Adding timer for hour, day, week, and zone because there is no single element
    #  for the timer_interval.
    timer_hour = BootstrapSelect("timer_hours")
    timer_day = BootstrapSelect("timer_days")
    timer_month = BootstrapSelect("timer_months")
    timer_week = BootstrapSelect("timer_weeks")
    time_zone = BootstrapSelect("time_zone")
    starting_date = Calendar("miq_date_1")
    hour = BootstrapSelect("start_hour")
    minute = BootstrapSelect("start_min")
    # Email
    emails_send = Checkbox("send_email_cb")
    from_email = TextInput(name="from")
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
            self.schedules.is_opened and
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
            self.schedules.is_opened and
            self.schedules.tree.currently_selected == ["All Schedules", self.context["object"].name]
        )


class ScheduleDetailsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == 'Schedule "{}"'.format(self.context["object"].name) and
            self.schedules.is_opened and
            self.schedules.tree.currently_selected == ["All Schedules", self.context["object"].name]
        )


@attr.s
class Schedule(Updateable, Pretty, BaseEntity):
    """Represents a schedule in Cloud Intel/Reports/Schedules.

    Args:
        name: Schedule name.
        description: Schedule description.
        report_filter: 3-tuple with filter selection (see the UI).
        active: Whether is this schedule active.
        timer: Specifies how often this schedule runs. It can be a dictionary that contains
                run, run_interval, starting_date, timezone, starting_hour and starting_minute
        from_email: Email from which scheduled report will be sent.
        emails: Contains list of emails where schedules emails will be sent.
                If specified, turns on e-mail sending. Can be string, or list or set.
        email_options: Tuple containing send_if_empty, send_csv, send_txt, send_pdf.
    """
    pretty_attrs = ["name", "report_filter"]

    def __str__(self):
        return self.name

    name = attr.ib()
    description = attr.ib()
    report_filter = attr.ib()
    active = attr.ib(default=None)
    timer = attr.ib(default=None)
    from_email = attr.ib(default=None)
    emails = attr.ib(default=None)
    email_options = attr.ib(default=None)

    @property
    def exists(self):
        schedules = self.appliance.db.client["miq_schedules"]
        return self.appliance.db.client.session\
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
        view = self.create_view(ScheduleDetailsView, override=updates, wait='10s')
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Schedule "{}" was saved'.format(updates.get("name", self.name)))
        else:
            view.flash.assert_message(
                'Edit of Schedule "{}" was cancelled by the user'.format(self.name))

    def delete(self, cancel=False):
        view = navigate_to(self, "Details")
        view.configuration.item_select("Delete this Schedule", handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
        else:
            view = self.create_view(SchedulesAllView)
            assert view.is_displayed
        view.flash.assert_no_error()

    def queue(self):
        """Queue this schedule."""
        view = navigate_to(self, "Details")
        view.configuration.item_select("Queue up this Schedule to run now")

    @property
    def enabled(self):
        view = navigate_to(self.parent, "All")
        for item in view.schedules_table.read():
            if item['Name'] == self.name:
                return item['Active'] == 'True'


@attr.s
class ScheduleCollection(BaseCollection):

    ENTITY = Schedule

    def create(self, name=None, description=None, report_filter=None, active=None,
               timer=None, from_email=None, emails=None, email_options=None):
        schedule = self.instantiate(name, description, report_filter, active=active, timer=timer,
            emails=emails, email_options=email_options)
        view = navigate_to(self, "Add")

        view.fill(
            {
                "name": name,
                "description": description,
                "active": active,
                "filter1": report_filter[0],
                "filter2": report_filter[1],
                "filter3": report_filter[2],
                "run": timer.get("run"),
                "timer_hour": timer.get("run_hour"),
                "timer_day": timer.get("run_day"),
                "timer_week": timer.get("run_week"),
                "timer_month": timer.get("run_month"),
                "time_zone": timer.get("time_zone"),
                "starting_date": timer.get("starting_date"),
                "hour": timer.get("starting_hour"),
                "minute": timer.get("starting_minute"),
                "emails_send": bool(emails),
                "from_email": from_email,
                "emails": emails,
                "send_if_empty": email_options.get("send_if_empty"),
                "send_txt": email_options.get("send_txt"),
                "send_csv": email_options.get("send_csv"),
                "send_pdf": email_options.get("send_pdf"),
            }
        )

        view.add_button.click()
        view = schedule.create_view(ScheduleDetailsView)
        assert view.is_displayed
        view.flash.assert_success_message('Schedule "{}" was added'.format(name))
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
                cell = view.schedules_table.row(name=name)[0]
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
        view.configuration.item_select(action)
        view.flash.assert_no_error()

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

    def step(self, *args, **kwargs):
        self.prerequisite_view.schedules.tree.click_path("All Schedules")


@navigator.register(ScheduleCollection, "Add")
class ScheduleNew(CFMENavigateStep):
    VIEW = NewScheduleView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        self.view.configuration.item_select("Add a new Schedule")


@navigator.register(Schedule, "Details")
class ScheduleDetails(CFMENavigateStep):
    VIEW = ScheduleDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self, *args, **kwargs):
        self.prerequisite_view.schedules.tree.click_path("All Schedules", self.obj.name)


@navigator.register(Schedule, "Edit")
class ScheduleEdit(CFMENavigateStep):
    VIEW = EditScheduleView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Edit this Schedule")
