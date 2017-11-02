# -*- coding: utf-8 -*-
"""Page model for Control / Explorer"""
import attr

from copy import copy
from navmazing import NavigateToAttribute, NavigateToSibling

from widgetastic.widget import Checkbox, Text, View
from widgetastic_manageiq import AlertEmail, SNMPForm, SummaryForm
from widgetastic_patternfly import BootstrapSelect, Button, Input

from . import ControlExplorerView
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable


class AlertsAllView(ControlExplorerView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == "All Alerts" and
            self.alerts.tree.currently_selected == ["All Alerts"]
        )


class AlertFormCommon(ControlExplorerView):
    description = Input(name="description")
    active = Checkbox("enabled_cb")
    severity = BootstrapSelect("miq_alert_severity")
    based_on = BootstrapSelect("miq_alert_db")

    @View.nested
    class evaluate(View):  # noqa
        type = BootstrapSelect("exp_name")
        # Real Time Performance Parameters
        performance_field = BootstrapSelect("perf_column")
        performance_field_operator = BootstrapSelect("select_operator")
        performance_field_value = Input(name="value_threshold")
        performance_trend = BootstrapSelect("trend_direction")
        performance_time_threshold = BootstrapSelect("rt_time_threshold")
        # Hardware Reconfigured Parameters
        hardware_attribute = BootstrapSelect("select_hdw_attr")
        operator = BootstrapSelect("select_operator")

        def fill(self, values):
            new_values = dict(type=values[0], **values[1])
            return View.fill(self, new_values)

    driving_event = BootstrapSelect("exp_event")
    notification_frequency = BootstrapSelect("repeat_time")
    snmp_trap_send = Checkbox("send_snmp_cb")
    snmp_trap = SNMPForm()
    timeline_event = Checkbox("send_evm_event_cb")
    mgmt_event_send = Checkbox("send_event_cb")
    mgmt_event = Input("event_name")
    cancel_button = Button("Cancel")
    emails_send = Checkbox("send_email_cb")
    emails = AlertEmail()


class NewAlertView(AlertFormCommon):
    title = Text("#explorer_title_text")

    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == "Adding a new Alert" and
            self.alerts.is_opened and
            self.alerts.tree.currently_selected == ["All Alerts"]
        )


class EditAlertView(AlertFormCommon):
    title = Text("#explorer_title_text")

    save_button = Button("Save")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == 'Editing Alert "{}"'.format(self.context["object"].description) and
            self.alerts.is_opened and
            self.alerts.tree.currently_selected == [
                "All Alerts",
                self.context["object"].description
            ]
        )


class AlertDetailsView(ControlExplorerView):
    title = Text("#explorer_title_text")
    info = SummaryForm("Info")
    hardware_reconfigured_parameters = SummaryForm("Hardware Reconfigured Parameters")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == 'Alert "{}"'.format(self.context["object"].description) and
            self.alerts.is_opened and
            self.alerts.tree.currently_selected == [
                "All Alerts",
                self.context["object"].description
            ]
        )


@attr.s
class Alert(BaseEntity, Updateable, Pretty):
    """Alert representation object.
    Example:
        >>> alert = Alert("my_alert", timeline_event=True, driving_event="Hourly Timer")
        >>> alert.create()
        >>> alert.delete()

    Args:
        description: Name of the Alert.
        based_on: Cluster, Datastore, Host, Provider, ...
        evaluate: Use it as follows:
            ``("What to Evaluate selection", dict(values="for form"))``.
            If you want to select Nothing, you will therefore pass ``("Nothing", {})``.
            Other example:

            .. code-block:: python

                    ("Hardware Reconfigured",
                     dict(hw_attribute="Number of CPUs", hw_attribute_operator="Increased")
                    )
        driving_event: This Alert's driving event (Hourly Timer, ...).
        notification_frequency: 1 Minute, 2 Minutes, ...
        snmp_trap: Whether to send snmp traps.
        emails: Whether to send e-mails. `False` disables, string or list of strings
            with emails enables.
        timeline_event: Whether generate a timeline event.
        mgmt_event: If specified as string, it will reveal the form and types it into the text box.
            If False, then it will be disabled. None - don't care.
    """

    pretty_attrs = ["description", "evaluate"]

    description = attr.ib()
    severity = attr.ib(default="Info")
    active = attr.ib(default=None)
    based_on = attr.ib(default=None)
    evaluate = attr.ib(default=None)
    driving_event = attr.ib(default=None)
    notification_frequency = attr.ib(default=None)
    snmp_trap = attr.ib(default=None)
    emails = attr.ib(default=None)
    timeline_event = attr.ib(default=None)
    mgmt_event = attr.ib(default=None)

    def __str__(self):
        """Conversion to string used when assigning in multibox selector."""
        return self.description

    def update(self, updates, cancel=False):
        """Update this Alert in UI.

        Args:
            updates: Provided by update() context manager.
            cancel: Whether to cancel the update (default False).
        """
        view = navigate_to(self, "Edit")
        for attrib, value in updates.items():
            setattr(self, attrib, value)
        changed = self._fill(view)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(AlertDetailsView, override=updates)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Alert "{}" was saved'.format(updates.get("description", self.description)))
        else:
            view.flash.assert_message(
                'Edit of Alert "{}" was cancelled by the user'.format(self.description))

    def delete(self, cancel=False):
        """Delete this Alert in UI.

        Args:
            cancel: Whether to cancel the deletion (default False).
        """
        view = navigate_to(self, "Details")
        view.configuration.item_select("Delete this Alert", handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view = self.create_view(AlertsAllView)
            assert view.is_displayed
            view.flash.assert_success_message(
                'Alert "{}": Delete successful'.format(self.description))

    def copy(self, **updates):
        """Copy this Alert in UI.

        Args:
            updates: updates for the alert.
        """
        view = navigate_to(self, "Copy")
        new_alert = copy(self)
        changed = view.fill(updates)
        if changed:
            view.add_button.click()
        else:
            view.cancel_button.click()
        for attrib, value in updates.items():
            setattr(new_alert, attrib, value)
        view = new_alert.create_view(AlertDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Alert "{}" was added'.format(updates.get("description", new_alert.description)))
        else:
            view.flash.assert_message("Add of new Alert was cancelled by the user")
        return new_alert

    def _fill(self, view):
        """This function prepares the values and fills the form."""
        fill_details = dict(
            description=self.description,
            active=self.active,
            severity=self.severity,
            based_on=self.based_on,
            evaluate=self.evaluate,
            driving_event=self.driving_event,
            notification_frequency=self.notification_frequency,
            timeline_event=self.timeline_event,
        )
        if self.mgmt_event is not None:
            # We have to check or uncheck the checkbox and then subsequently handle the form fill
            if not self.mgmt_event:
                fill_details["mgmt_event_send"] = False
                fill_details["mgmt_event"] = None
            else:
                fill_details["mgmt_event_send"] = True
                fill_details["mgmt_event"] = self.mgmt_event
        if self.snmp_trap is not None:
            if not self.snmp_trap:
                fill_details["snmp_trap_send"] = False
                fill_details["snmp_trap"] = None
            else:
                fill_details["snmp_trap_send"] = True
                fill_details["snmp_trap"] = self.snmp_trap
        if self.emails is not None:
            if not self.emails:
                fill_details["emails_send"] = False
                fill_details["emails"] = None
            else:
                fill_details["emails_send"] = True
                fill_details["emails"] = self.emails
        return view.fill(fill_details)

    @property
    def exists(self):
        """Check existence of this Alert.

        Returns: :py:class:`bool` signalizing the presence of the Alert in the database.
        """
        alerts = self.appliance.db.client["miq_alerts"]
        return self.appliance.db.client.session\
            .query(alerts.description)\
            .filter(alerts.description == self.description)\
            .count() > 0


class AlertCollection(BaseCollection):

    ENTITY = Alert

    def create(self, description, severity="Info", active=None, based_on=None, evaluate=None,
            driving_event=None, notification_frequency=None, snmp_trap=None, emails=None,
            timeline_event=None, mgmt_event=None):
        severity = None if self.appliance.version < "5.9" else severity
        alert = self.instantiate(description, severity=severity, active=active, based_on=based_on,
            evaluate=evaluate, driving_event=driving_event,
            notification_frequency=notification_frequency, snmp_trap=snmp_trap, emails=emails,
            timeline_event=timeline_event, mgmt_event=mgmt_event)
        view = navigate_to(self, "Add")
        alert._fill(view)
        view.add_button.click()
        view = alert.create_view(AlertDetailsView)
        assert view.is_displayed
        view.flash.assert_success_message('Alert "{}" was added'.format(alert.description))
        return alert


@navigator.register(AlertCollection, "All")
class AlertsAll(CFMENavigateStep):
    VIEW = AlertsAllView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.prerequisite_view.alerts.tree.click_path("All Alerts")


@navigator.register(AlertCollection, "Add")
class AlertNew(CFMENavigateStep):
    VIEW = NewAlertView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.configuration.item_select("Add a New Alert")


@navigator.register(Alert, "Edit")
class AlertEdit(CFMENavigateStep):
    VIEW = EditAlertView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.configuration.item_select("Edit this Alert")


@navigator.register(Alert, "Details")
class AlertDetails(CFMENavigateStep):
    VIEW = AlertDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self):
        self.prerequisite_view.alerts.tree.click_path("All Alerts", self.obj.description)


@navigator.register(Alert, "Copy")
class AlertCopy(CFMENavigateStep):
    VIEW = NewAlertView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.configuration.item_select("Copy this Alert", handle_alert=True)
