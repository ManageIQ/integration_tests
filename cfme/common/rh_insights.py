# -*- coding: utf-8 -*-
import attr

from navmazing import NavigateToAttribute
from cfme.base.login import BaseLoggedInPage
from widgetastic_manageiq import Table
from widgetastic.widget import Widget
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator


class IFrameText(Widget):
    """ The widget in RH Insights page are under iframe div, directly can't read with the Text
    Widget.

    Args:
        locator(str): location of the widget under iframe
        url(str): iframe url
    Returns:
        :py:class:`string` for passed locator
    """
    def __init__(self, parent, locator, url, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.url = url
        self.locator = locator

    def read(self):
        frame = self.browser.selenium.find_element_by_xpath(
            '//iframe[contains(@src, {})]'.format(self.url))
        self.browser.selenium.switch_to_frame(frame)
        return self.browser.text(self.locator)

    @property
    def is_displayed(self):
        return self.browser.is_displayed(self.locator)


class InventoryView(BaseLoggedInPage):

    table = Table(locator='//table[contains(@class, "table")]')
    title = IFrameText(locator='//*[contains(@class, "page-title")]',
                       url="/redhat_access/insights/inventory")
    systems = IFrameText(locator='//*[contains(@class, "system-count")]',
                         url="/redhat_access/insights/inventory")

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Red Hat Insights', 'Inventory'])


class OverviewView(BaseLoggedInPage):

    title = IFrameText(locator='//*[contains(@class, "page-title")]',
                       url="/redhat_access/insights/overview")

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Red Hat Insights', 'Overview'])


class ActionsView(BaseLoggedInPage):
    title = IFrameText(locator='//*[contains(@class, "page-title")]',
                       url="/redhat_access/insights/actions")

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Red Hat Insights', 'Actions'])


class RulesView(BaseLoggedInPage):
    title = IFrameText(locator='//*[contains(@class, "page-title")]',
                       url="/redhat_access/insights/rules")

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Red Hat Insights', 'Rules'])


@attr.s
class RHInsights(BaseEntity):

    _param_name = "RHInsights"
    name = attr.ib()


@attr.s
class RHInsightsCollection(BaseCollection):
    """Collection object for the :py:class:`cmfe.infrastructure.networking.InfraNetworking`."""
    ENTITY = RHInsights


@navigator.register(RHInsightsCollection, 'Inventory')
class InventoryAll(CFMENavigateStep):
    VIEW = InventoryView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        if self.appliance.version >= 5.9:
            self.prerequisite_view.navigation.select('Red Hat Insights', 'Inventory')
        else:
            self.prerequisite_view.navigation.select('Red Hat Insights', 'Systems')


@navigator.register(RHInsightsCollection, 'Overview')
class OverviewAll(CFMENavigateStep):
    VIEW = OverviewView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Red Hat Insights', 'Overview')


@navigator.register(RHInsightsCollection, 'Actions')
class ActionsAll(CFMENavigateStep):
    VIEW = ActionsView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Red Hat Insights', 'Actions')


@navigator.register(RHInsightsCollection, 'Rules')
class RulesAll(CFMENavigateStep):
    VIEW = RulesView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Red Hat Insights', 'Rules')
