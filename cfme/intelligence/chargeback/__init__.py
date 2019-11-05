# -*- coding: utf-8 -*-
from widgetastic.widget import View
from widgetastic_patternfly import Accordion

from cfme.common import BaseLoggedInPage
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
