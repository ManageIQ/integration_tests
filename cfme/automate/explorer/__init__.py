# -*- coding: utf-8 -*-
import re

from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown

from cfme.base import Server
from cfme.common import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Splitter


try:
    Pattern = re.Pattern
except AttributeError:
    Pattern = re._pattern_type


class AutomateExplorerView(BaseLoggedInPage):
    @property
    def in_explorer(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Automation", "Automate", "Explorer"]
        )

    @property
    def is_displayed(self):
        return self.in_explorer and not self.datastore.is_dimmed

    @View.nested
    class datastore(Accordion):  # noqa
        tree = ManageIQTree()
        splitter = Splitter()

    configuration = Dropdown('Configuration')


@navigator.register(Server)
class AutomateExplorer(CFMENavigateStep):
    VIEW = AutomateExplorerView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self, *args, **kwargs):
        self.view.navigation.select(*["Automation", "Automate", "Explorer"])


def check_tree_path(actual, desired, partial=False):
    # keyword argument - 'partial'  is introduced here because of unexpected behaviour of automate
    # tree accordions. In this case, actual and desired trees will not be same which creates problem
    # For more details please refer:
    # https://github.com/ManageIQ/integration_tests/pull/8358#discussion_r247770688
    if len(actual) != len(desired) and not partial:
        return False
    # We don't care about icons because we also match titles, which give the type away
    for actual_item, desired_item in zip(actual, without_icons(desired)):
        if isinstance(desired_item, Pattern):
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
