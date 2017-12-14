# -*- coding: utf-8 -*-
from widgetastic.widget import Text, View
from widgetastic_manageiq import Accordion, ManageIQTree, DialogButton, DragandDropElements
from widgetastic_patternfly import Button, Dropdown, Input

from cfme.base.login import BaseLoggedInPage
from cfme.base.ui import automate_menu_name


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
    class service_dialogs(Accordion):  # noqa
        ACCORDION_NAME = 'Service Dialogs'
        tree = ManageIQTree()

    configuration = Dropdown('Configuration')


class DialogForm(AutomateCustomizationView):
    title = Text('#explorer_title_text')

    label = Input(id='name')
    description = Input(id="description")
    save = Button('Save')
    cancel = Button('Cancel')


class AddDialogView(DialogForm):
    create_tab = Text(locator='.//li/a[contains(@class, "create-tab")]')

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.create_tab.is_displayed
        )


class EditDialogView(DialogForm):
    save_button = Button('Save')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.label.text == self.label
        )


class TabForm(AddDialogView):

    tab_label = Input(id='label')
    tab_desc = Input(name="description")
    save_button = DialogButton('Save')
    cancel_button = DialogButton('Cancel')


class AddTabView(TabForm):
    box = Text(locator='.//div[contains(@class, "panel-heading")]/strong')
    add_section = Text(locator='.//div/i[normalize-space(.)="fa-plus-circle"]')
    new_tab = Text(locator='.//a[normalize-space(.)="New tab"]')
    edit_tab = Text(locator='.//a[normalize-space(.)="New tab"]'
                            '/i[contains(@class, "pficon-edit")]')

    @property
    def is_displayed(self):
        return self.in_customization and self.box.is_displayed


class BoxForm(AddTabView):
    box_label = Input(id='label')
    box_desc = Input(name="description")
    save_button = DialogButton('Save')
    cancel_button = DialogButton('Cancel')


class AddBoxView(BoxForm):
    """AddBox View."""

    component = Text(
        locator='.//div[normalize-space(.)="Drag items here to add to the dialog. At '
                'least one item is required before saving"]')
    dd = DragandDropElements()
    new_box = Text(locator='.//div[normalize-space(.)="New section"]')
    edit_box = Text(locator='.//div[normalize-space(.)="New section"]'
                            '/i[contains(@class, "pficon-edit")]')

    @property
    def is_displayed(self):
        return self.in_customization and self.component.is_displayed
