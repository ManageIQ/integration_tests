# -*- coding: utf-8 -*-
import re

from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_manageiq import Accordion, ManageIQTree
from widgetastic_patternfly import Dropdown, FlashMessages

from cfme import BaseLoggedInPage
from cfme.base import Server
from utils.appliance.implementations.ui import navigator, CFMENavigateStep


class AutomateExplorerView(BaseLoggedInPage):
    flash = FlashMessages('.//div[starts-with(@id, "flash_text_div")]')

    @property
    def in_explorer(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Automate', 'Explorer'])

    @property
    def is_displayed(self):
        return self.in_explorer and self.configuration.is_displayed and not self.datastore.is_dimmed

    @View.nested
    class datastore(Accordion):  # noqa

        tree = ManageIQTree()

    configuration = Dropdown('Configuration')


@navigator.register(Server)
class AutomateExplorer(CFMENavigateStep):
    VIEW = AutomateExplorerView
    prerequisite = NavigateToSibling('LoggedIn')

    # Repeat if alert because you might be at a page that asks you if you really want to leave
    @CFMENavigateStep.repeat_if_alert(accept=True)
    def step(self):
        self.view.navigation.select('Automate', 'Explorer')


def check_tree_path(actual, desired):
    if len(actual) != len(desired):
        return False
    for actual_item, desired_item in zip(actual, desired):
        if isinstance(desired_item, re._pattern_type):
            if desired_item.match(actual_item) is None:
                return False
        else:
            if desired_item != actual_item:
                return False
    else:
        return True
