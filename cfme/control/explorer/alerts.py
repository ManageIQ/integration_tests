"""Page model for Control / Explorer"""
from copy import copy

import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import Checkbox
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input
from widgetastic_patternfly import SelectorDropdown

from cfme.common import BaseLoggedInPage
from cfme.control.explorer import ControlExplorerView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from widgetastic_manageiq import AlertEmail
from widgetastic_manageiq import MonitorStatusCard
from widgetastic_manageiq import SNMPForm
from widgetastic_manageiq import SummaryForm
from widgetastic_manageiq import Table
from widgetastic_manageiq.expression_editor import ExpressionEditor


class MonitorOverviewView(BaseLoggedInPage):
    """ Provide a view for the Monitor->Alerts->Overview page """
    # since the status_card depends on the provider of the fired alert, it must be instantiated as:
    # status_card = view.status_card(<provider_name>)
    status_card = MonitorStatusCard
    # Used for Ascending/Descending sort
    sort_order = Text(".//button[./span[contains(@class,'sort-direction')]]")
    # Used to select filter_by items like 'Name', 'Severity'
    filter_by_dropdown = SelectorDropdown('uib-tooltip', 'Filter by')
    # Used to select sort by options like 'Name', 'Number of Associated Plans'
    sort_by_dropdown = SelectorDropdown('class', 'btn btn-default ng-binding dropdown-toggle')
    # Used to set group by
    group_by = BootstrapSelect(
        locator=(
            './/div[contains(@class, "bootstrap-select")] '
            '/button[normalize-space(@title)="Environment"]/..'
        )
    )
    # Used to set display
    display = BootstrapSelect(
        locator=(
            './/div[contains(@class, "bootstrap-select")] '
            '/button[normalize-space(@title)="providers"]/..'
        )
    )

    @property
    def in_monitor_alerts_overview(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Monitor', 'Alerts', 'Overview']
        )

    @property
    def is_displayed(self):
        return self.in_monitor_alerts_overview


class AlertsAllView(ControlExplorerView):
    title = Text("#explorer_title_text")
    table = Table(".//div[@id='alert_list_div' or @class='miq-data-table']/table")

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
        # Expression Parameters
        expression = ExpressionEditor("//button[normalize-space(.)='Define Expression']")

        def fill(self, values):
            if isinstance(values, str):
                new_values = dict(type=values)
            elif isinstance(values, (list, tuple)):
                new_values = dict(type=values[0], **values[1])
            else:
                raise TypeError("Evaluate part should be a string or tuple.")
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
        # NewAlertView is used for adding and copying alerts. But selected trees gets changes.
        # So need to add if-else block for getting correct currently selected tree.
        if self.description.value:
            # This tree gets selected whenever we are going to copy old alert.
            # Here we can able to get description value of old alert.
            currently_selected_tree = ["All Alerts", self.context['object'].description]
        else:
            # This tree gets selected whenever we are going to create new alert.
            # So we can not get any description value available there.
            currently_selected_tree = ["All Alerts"]

        return (
            self.in_control_explorer and
            self.title.text == "Adding a new Alert" and
            self.alerts.is_opened and
            self.alerts.tree.currently_selected == currently_selected_tree
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
        >>> alert = appliance.collections.alerts.create(
        >>>    "my_alert",
        >>>    timeline_event=True,
        >>>    driving_event="Hourly Timer"
        >>> )
        >>> alert.delete()

    Attributes:
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
    severity = attr.ib(default=None)
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
        return str(self.description)

    def update(self, updates):
        """Update this Alert in UI.

        Args:
            updates: Provided by update() context manager.
        """
        view = navigate_to(self, "Edit")
        for attrib, value in updates.items():
            setattr(self, attrib, value)
        changed = self._fill(view)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(AlertDetailsView, override=updates, wait='10s')
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
        view = new_alert.create_view(AlertDetailsView, wait='10s')
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

    def create(self, description, severity=None, active=None, based_on=None, evaluate=None,
            driving_event=None, notification_frequency=None, snmp_trap=None, emails=None,
            timeline_event=True, mgmt_event=None):
        """ Create a new alert in the UI.

            Note: Since alerts in CFME require a description, driving_event or evaluate, and one
            of snmp_trap, emails, timeline_event, or mgmt_event, we set defaults to
            timeline_event=True, and driving_event=<first_item_from_dropdown>
            We select the first item from the dropdown for efficiency.
            The driving event is only selected if evaluate is None.

            This allows creation of an alert only by a description. e.g.
            >>> alert = appliance.collections.alerts.create('my_alert_description')
            >>> alert.delete()
        """
        view = navigate_to(self, "Add")
        if driving_event is None and evaluate is None:
            driving_event = view.driving_event.all_options[1].text
        if severity is None and self.appliance.version >= "5.11.0.7":
            # set default severity to "Info" only for "5.11"
            severity = view.severity.all_options[1].text
        # instantiate the alert
        alert = self.instantiate(description, severity=severity, active=active, based_on=based_on,
            evaluate=evaluate, driving_event=driving_event,
            notification_frequency=notification_frequency, snmp_trap=snmp_trap, emails=emails,
            timeline_event=timeline_event, mgmt_event=mgmt_event)
        alert._fill(view)
        view.add_button.click()
        view = alert.create_view(AlertDetailsView, wait='10s')
        view.flash.assert_success_message('Alert "{}" was added'.format(alert.description))
        return alert

    def all(self):
        # get alerts via reading 'All Alerts table'
        view = navigate_to(self.appliance.collections.alerts, 'All')
        try:
            alerts = [
                self.instantiate(
                    description=alert.get('Description'),
                    active=alert.get('Active'),
                    based_on=alert.get('Based On'),
                    evaluate=alert.get('What is evaluated'),
                    emails=alert.get('Email'),
                    snmp_trap=alert.get('SNMP'),
                    timeline_event=alert.get('Event on Timeline'),
                    mgmt_event=alert.get('Management Event Raised')
                )
                for alert in view.table.read()
            ]
        except NoSuchElementException:
            logger.exception('AlertCollection: Table not found in Alerts All view')
            return None
        return alerts


@navigator.register(AlertCollection, "All")
class AlertsAll(CFMENavigateStep):
    VIEW = AlertsAllView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self, *args, **kwargs):
        self.prerequisite_view.alerts.tree.click_path("All Alerts")


@navigator.register(AlertCollection, "Add")
class AlertNew(CFMENavigateStep):
    VIEW = NewAlertView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Add a New Alert")


@navigator.register(Alert, "Edit")
class AlertEdit(CFMENavigateStep):
    VIEW = EditAlertView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Edit this Alert")


@navigator.register(Alert, "Details")
class AlertDetails(CFMENavigateStep):
    VIEW = AlertDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.alerts.tree.click_path("All Alerts", self.obj.description)


@navigator.register(Alert, "Copy")
class AlertCopy(CFMENavigateStep):
    VIEW = NewAlertView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Copy this Alert", handle_alert=True)


@navigator.register(AlertCollection)
class MonitorOverview(CFMENavigateStep):
    VIEW = MonitorOverviewView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Monitor", "Alerts", "Overview")
