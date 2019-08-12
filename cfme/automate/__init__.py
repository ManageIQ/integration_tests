# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling
from widgetastic.widget import Checkbox
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import Input

from cfme.base import Server
from cfme.common import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import ManageIQTree


class AutomateCustomizationView(BaseLoggedInPage):
    # TODO re-model this so it can be nested as a sidebar instead of inherited
    @property
    def in_customization(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Automation", "Automate", "Customization"]
        )

    @property
    def is_displayed(self):
        return (self.in_customization and
                self.buttons.is_displayed and
                not self.buttons.is_dimmed)

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

    def step(self, *args, **kwargs):
        self.view.navigation.select(*["Automation", "Automate", "Customization"])


class DialogForm(AutomateCustomizationView):
    title = Text('#explorer_title_text')

    plus_btn = Dropdown('Add')
    label = Input(name='label')
    description = Input(name="description")

    submit_btn = Checkbox(name='chkbx_submit')
    cancel_btn = Checkbox(name='chkbx_cancel')


class AddDialogView(DialogForm):

    add_button = Button("Add")
    plus_btn = Dropdown('Add')

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == "Adding a new Dialog [Dialog Information]"
        )


class EditDialogView(DialogForm):
    element_tree = ManageIQTree('dialog_edit_treebox')

    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == "Editing Dialog {}".format(self.label)
        )


class TabForm(AddDialogView):
    tab_label = Input(name='tab_label')
    tab_desc = Input(name="tab_description")


class AddTabView(TabForm):

    plus_btn = Dropdown('Add')

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == "Adding a new Dialog [Tab Information]"
        )


class BoxForm(AddTabView):
    box_label = Input(name='group_label')
    box_desc = Input(name="group_description")


class AddBoxView(BoxForm):
    """AddBox View."""
    plus_btn = Dropdown('Add')

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == "Adding a new Dialog [Box Information]"
        )
