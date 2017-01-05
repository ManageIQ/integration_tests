# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_manageiq import ManageIQTree
from widgetastic_patternfly import Accordion, Dropdown

from cfme import BaseLoggedInPage
from cfme.base import Server
from utils.appliance.implementations.ui import navigator, CFMENavigateStep


class ControlExplorerView(BaseLoggedInPage):

    @property
    def is_displayed(self):
        return (self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Control', 'Explorer'])

    @View.nested
    class policy_profiles(Accordion):  # noqa
        ACCORDION_NAME = "Policy Profiles"

        tree = ManageIQTree()

    @View.nested
    class policies(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class events(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class conditions(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class actions(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class alert_profiles(Accordion):  # noqa
        ACCORDION_NAME = "Alert Profiles"

        tree = ManageIQTree()

    @View.nested
    class alerts(Accordion):  # noqa
        tree = ManageIQTree()

    configuration = Dropdown("Configuration")


@navigator.register(Server)
class ControlExplorer(CFMENavigateStep):
    VIEW = ControlExplorerView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self):
        self.view.navigation.select("Control", "Explorer")
