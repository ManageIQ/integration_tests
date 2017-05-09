# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_manageiq import Accordion, ManageIQTree
from widgetastic_patternfly import Dropdown

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.base.ui import automate_menu_name
from utils.appliance.implementations.ui import navigator, CFMENavigateStep


class AutomateCustomizationView(BaseLoggedInPage):
    @property
    def in_customization(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == automate_menu_name(
                self.context['object'].appliance) + ['Customization'])

    @property
    def is_displayed(self):
        return self.in_customization and self.configuration.is_displayed

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
