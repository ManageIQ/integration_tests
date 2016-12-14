# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_manageiq import ManageIQTree
from widgetastic_patternfly import Accordion, Dropdown

from cfme import BaseLoggedInPage
from cfme.base import Server
from utils.appliance.implementations.ui import navigator, CFMENavigateStep


def automate_menu_name(appliance):
    if appliance.version < '5.8':
        return ['Automate']
    else:
        return ['Automation', 'Automate']


class AutomateCustomizationView(BaseLoggedInPage):
    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == automate_menu_name(
                self.obj.appliance) + ['Customization'])

    @View.nested
    class provisioning_dialogs(Accordion):  # noqa
        ACCORDION_NAME = 'Provisioning Dialogs'

        tree = ManageIQTree()

    @View.nested
    class service_dialogs(Accordion):  # noqa
        ACCORDION_NAME = 'Service Dialogs'

        tree = ManageIQTree()

    @View.nested
    class buttons(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class import_export(Accordion):  # noqa
        ACCORDION_NAME = 'Import/Export'

        tree = ManageIQTree()

    configuration = Dropdown('Configuration')


@navigator.register(Server)
class AutomateCustomization(CFMENavigateStep):
    VIEW = AutomateCustomizationView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        self.view.navigation.select(*automate_menu_name(self.obj.appliance) + ['Customization'])


class AutomateExplorerView(BaseLoggedInPage):
    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == automate_menu_name(
                self.obj.appliance) + ['Explorer'])

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
