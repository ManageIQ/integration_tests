import re
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text

from cfme.base.ssui import SSUIBaseLoggedInPage
from cfme.services.dashboard import Dashboard
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ssui import (
    navigator,
    SSUINavigateStep,
    navigate_to,
    ViaSSUI,
)
from cfme.utils.wait import wait_for
from widgetastic_manageiq import (SSUIPrimarycard, SSUIAggregatecard,
                                  SSUIlist, SSUIPaginationPane)


class DashboardView(SSUIBaseLoggedInPage):
    dashboard_card = SSUIPrimarycard()
    aggregate_card = SSUIAggregatecard()

    @property
    def in_dashboard(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["", "Dashboard"] and
            self.dashboard_card.is_displayed)

    @property
    def is_displayed(self):
        return self.in_dashboard


class MyServiceForm(SSUIBaseLoggedInPage):

    service = SSUIlist(list_name='serviceList')


class MyServicesView(MyServiceForm):
    title = Text(locator='//li[@class="active"]')
    results = Text(locator='//div[contains(@class, "toolbar-pf-results")]/*/h5')
    paginator = SSUIPaginationPane()

    @property
    def in_myservices(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["", "My Services"])

    @property
    def is_displayed(self):
        return self.in_myservices and self.title.text == "My Services"


@MiqImplementationContext.external_for(Dashboard.num_of_rows, ViaSSUI)
def num_of_rows(self):
    """Returns the number of rows/services displayed
       in paginator"""

    view = self.create_view(MyServicesView)
    view.paginator.set_items_per_page("100 items")
    rows = view.paginator.items_amount
    return rows


@MiqImplementationContext.external_for(Dashboard.results, ViaSSUI)
def results(self):
    """Returns the count of services displayed at the top of page"""
    view = self.create_view(MyServicesView)
    result = view.results.text
    int_result = re.search(r'\d+', result).group()
    if self.appliance.version >= "5.8":
        assert int_result == self.num_of_rows()
    return int_result


@MiqImplementationContext.external_for(Dashboard.total_services, ViaSSUI)
def total_services(self):
    """Returns the total services(Integer) displayed on dashboard"""

    view = navigate_to(self, 'DashboardAll')
    total_service = view.dashboard_card.get_count('Total Services')
    view = navigate_to(self, 'TotalServices')
    view.flash.assert_no_error()
    view = self.create_view(MyServicesView)
    wait_for(
        lambda: view.is_displayed, delay=15, num_sec=300,
        message="waiting for view to be displayed"
    )
    assert view.is_displayed
    return total_service


@MiqImplementationContext.external_for(Dashboard.total_requests, ViaSSUI)
def total_requests(self):
    """Total Request cannot be clicked so this method just
    returns the total number of requests displayed on dashboard.
    """

    view = navigate_to(self, 'DashboardAll')
    total_request = view.dashboard_card.get_count('Total Requests')
    return total_request


@MiqImplementationContext.external_for(Dashboard.pending_requests, ViaSSUI)
def pending_requests(self):
    """Pending Request cannot be clicked so this method just
    returns the total number of requests displayed on dashboard.
    """

    view = navigate_to(self, 'DashboardAll')
    pending_request = view.aggregate_card.get_count('Pending Requests')
    return pending_request


@MiqImplementationContext.external_for(Dashboard.approved_requests, ViaSSUI)
def approved_requests(self):
    """Approved Request cannot be clicked so this method just
    returns the total number of requests displayed on dashboard.
    """

    view = navigate_to(self, 'DashboardAll')
    approved_request = view.aggregate_card.get_count('Approved Requests')
    return approved_request


@MiqImplementationContext.external_for(Dashboard.denied_requests, ViaSSUI)
def denied_requests(self):
    """Denied Request cannot be clicked so this method just
    returns the total number of requests displayed on dashboard.
    """

    view = navigate_to(self, 'DashboardAll')
    denied_request = view.aggregate_card.get_count('Denied Requests')
    return denied_request


@MiqImplementationContext.external_for(Dashboard.retiring_soon, ViaSSUI)
def retiring_soon(self):
    """Returns the count of retiring soon services displayed on dashboard"""

    view = navigate_to(self, 'DashboardAll')
    retiring_services = view.aggregate_card.get_count('Retiring Soon')
    view = navigate_to(self, 'RetiringSoon')
    view.flash.assert_no_error()
    view = self.create_view(MyServicesView)
    wait_for(
        lambda: view.is_displayed, delay=15, num_sec=300,
        message="waiting for view to be displayed"
    )
    assert view.is_displayed
    return retiring_services


@MiqImplementationContext.external_for(Dashboard.current_services, ViaSSUI)
def current_services(self):
    """Returns the count of active services displayed on dashboard"""

    view = navigate_to(self, 'DashboardAll')
    current_service = view.aggregate_card.get_count('Current Services')
    view = navigate_to(self, 'CurrentServices')
    view.flash.assert_no_error()
    view = self.create_view(MyServicesView)
    wait_for(
        lambda: view.is_displayed, delay=15, num_sec=300,
        message="waiting for view to be displayed"
    )
    assert view.is_displayed
    return current_service


@MiqImplementationContext.external_for(Dashboard.retired_services, ViaSSUI)
def retired_services(self):
    """Returns the count of retired services displayed on dashboard"""

    view = navigate_to(self, 'DashboardAll')
    retired_service = view.aggregate_card.get_count('Retired Services')
    view = navigate_to(self, 'RetiredServices')
    view.flash.assert_no_error()
    view = self.create_view(MyServicesView)
    wait_for(
        lambda: view.is_displayed, delay=15, num_sec=300,
        message="waiting for view to be displayed"
    )
    assert view.is_displayed
    return retired_service


@MiqImplementationContext.external_for(Dashboard.monthly_charges, ViaSSUI)
def monthly_charges(self):
    """Returns the chargeback data displayed on dashboard"""

    view = navigate_to(self, 'DashboardAll')
    return view.aggregate_card.get_count('Monthly Charges - This Month To Date')


@navigator.register(Dashboard, 'DashboardAll')
class DashboardAll(SSUINavigateStep):
    VIEW = DashboardView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Dashboard')


@navigator.register(Dashboard, 'TotalServices')
class TotalServices(SSUINavigateStep):
    VIEW = MyServicesView

    prerequisite = NavigateToSibling('DashboardAll')

    def step(self, *args, **kwargs):
        self.prerequisite_view.dashboard_card.click_at("Total Services")


@navigator.register(Dashboard, 'RetiringSoon')
class RetiringSoon(SSUINavigateStep):
    VIEW = MyServicesView

    prerequisite = NavigateToSibling('DashboardAll')

    def step(self, *args, **kwargs):
        self.prerequisite_view.aggregate_card.click_at("Retiring Soon")


@navigator.register(Dashboard, 'CurrentServices')
class CurrentServices(SSUINavigateStep):
    VIEW = MyServicesView

    prerequisite = NavigateToSibling('DashboardAll')

    def step(self, *args, **kwargs):
        self.prerequisite_view.aggregate_card.click_at("Current Services")


@navigator.register(Dashboard, 'RetiredServices')
class RetiredServices(SSUINavigateStep):
    VIEW = MyServicesView

    prerequisite = NavigateToSibling('DashboardAll')

    def step(self, *args, **kwargs):
        self.prerequisite_view.aggregate_card.click_at("Retired Services")
