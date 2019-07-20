# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_patternfly import Accordion

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import ManageIQTree


class ChargebackView(BaseLoggedInPage):

    @property
    def in_chargeback(self):
        return (
            self.logged_in_as_current_user
            and self.navigation.currently_selected
            == [self.context["object"].appliance.server.intel_name, "Chargeback"]
        )

    @property
    def is_displayed(self):
        return self.in_chargeback

    @View.nested
    class reports(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class rates(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class assignments(Accordion):  # noqa
        tree = ManageIQTree()


@navigator.register(Server)
class IntelChargeback(CFMENavigateStep):
    VIEW = ChargebackView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select(
            self.view.context["object"].intel_name, "Chargeback"
        )
