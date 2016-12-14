# -*- coding: utf-8 -*-
"""Page model for Control / Explorer"""
from utils.pretty import Pretty
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from navmazing import NavigateToAttribute

from widgetastic.widget import Text, Checkbox
from widgetastic_patternfly import BootstrapSelect, Button, Input
from widgetastic_manageiq import SNMPForm

from . import ControlExplorerView
from utils.appliance import Navigatable
from utils.update import Updateable

from copy import copy


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
    based_on = BootstrapSelect("miq_alert_db")
    driving_event = BootstrapSelect("exp_event")
    notification_frequency = BootstrapSelect("repeat_time")
    snmp_trap_send = Checkbox("send_snmp_cb")
    snmp_trap = SNMPForm()
    timeline_event = Checkbox("send_evm_event_cb")
    mgmt_event_send = Checkbox("send_event_cb")
    mgmt_event = Input("event_name")
    cancel_button = Button("Cancel")


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


class Alert(Updateable, Navigatable, Pretty):
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
        snmp_trap: Not Implemented
        emails: Whether to send e-mails. `False` disables, string or list of strings
            with emails enables.
        timeline_event: Whether generate a timeline event.
        mgmt_event: If specified as string, it will reveal the form and types it into the text box.
            If False, then it will be disabled. None - don't care.
    """

    pretty_attrs = ["description", "evaluate"]

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
                 mgmt_event=None,
                 appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.description = description
        self.active = active
        self.based_on = based_on
        if evaluate is not None:
            raise NotImplementedError
        self.driving_event = driving_event
        self.notification_frequency = notification_frequency
        self.snmp_trap = snmp_trap
        if emails is not None:
            raise NotImplementedError
        self.timeline_event = timeline_event
        self.mgmt_event = mgmt_event

    def __str__(self):
        "Conversion to string used when assigning in multibox selector."
        return self.description

    def create(self):
        "Create this Alert in UI."
        view = navigate_to(self, "Add")
        self._fill(view)
        view.add_button.click()
        view = self.create_view(AlertDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_message('Alert "{}" was added'.format(self.description))

    def update(self, updates, cancel=False):
        """Update this Alert in UI.

        Args:
            updates: Provided by update() context manager.
            cancel: Whether to cancel the update (default False).
        """
        view = navigate_to(self, "Edit")
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        for attr, value in updates.items():
            setattr(self, attr, value)
        view = self.create_view(AlertDetailsView)
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
            view.flash.assert_no_error()
            view.flash.assert_message('Alert "{}": Delete successful'.format(self.description))

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
        for attr, value in updates.items():
            setattr(new_alert, attr, value)
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
            based_on=self.based_on,
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
        view.fill(fill_details)

    @property
    def exists(self):
        """Check existence of this Alert.

        Returns: :py:class:`bool` signalizing the presence of the Alert in the database.
        """
        alerts = self.appliance.db["miq_alerts"]
        return self.appliance.db.session\
            .query(alerts.description)\
            .filter(alerts.description == self.description)\
            .count() > 0


@navigator.register(Alert, "Add")
class AlertNew(CFMENavigateStep):
    VIEW = NewAlertView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.alerts.tree.click_path("All Alerts")
        self.view.configuration.item_select("Add a New Alert")


@navigator.register(Alert, "Edit")
class AlertEdit(CFMENavigateStep):
    VIEW = EditAlertView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.alerts.tree.click_path("All Alerts", self.obj.description)
        self.view.configuration.item_select("Edit this Alert")


@navigator.register(Alert, "Details")
class AlertDetails(CFMENavigateStep):
    VIEW = AlertDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.alerts.tree.click_path("All Alerts", self.obj.description)


@navigator.register(Alert, "Copy")
class AlertCopy(CFMENavigateStep):
    VIEW = NewAlertView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.alerts.tree.click_path("All Alerts", self.obj.description)
        self.view.configuration.item_select("Copy this Alert", handle_alert=True)
