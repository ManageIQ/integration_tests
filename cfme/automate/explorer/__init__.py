# -*- coding: utf-8 -*-
import re
from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.base.ui import automate_menu_name
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from widgetastic_manageiq import Accordion, ManageIQTree


class AutomateExplorerView(BaseLoggedInPage):
    @property
    def in_explorer(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == automate_menu_name(
                self.context['object'].appliance) + ['Explorer'])

    @property
    def is_displayed(self):
        return self.in_explorer and not self.datastore.is_dimmed

    @View.nested
    class datastore(Accordion):  # noqa
        tree = ManageIQTree()

    configuration = Dropdown('Configuration')


@navigator.register(Server)
class AutomateExplorer(CFMENavigateStep):
    VIEW = AutomateExplorerView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        self.view.navigation.select(*automate_menu_name(self.obj.appliance) + ['Explorer'])


def check_tree_path(actual, desired):
    if len(actual) != len(desired):
        return False
    # We don't care about icons because we also match titles, which give the type away
    for actual_item, desired_item in zip(actual, without_icons(desired)):
        if isinstance(desired_item, re._pattern_type):
            if desired_item.match(actual_item) is None:
                return False
        else:
            if desired_item != actual_item:
                return False
    else:
        return True


def without_icons(tree_path):
    """Tree paths with icons have tuples as steps with the icon being the first one."""
    processed = []
    for item in tree_path:
        if isinstance(item, tuple):
            item = item[1]
        processed.append(item)
    return processed
