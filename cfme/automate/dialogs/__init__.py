from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import Input

from cfme.common import BaseLoggedInPage
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import DialogButton
from widgetastic_manageiq import DialogElement
from widgetastic_manageiq import DragandDropElements
from widgetastic_manageiq import ManageIQTree


class AutomateCustomizationView(BaseLoggedInPage):
    @property
    def in_customization(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Automation", "Automate", "Customization"]
        )

    @property
    def is_displayed(self):
        return self.in_customization and self.configuration.is_displayed

    @View.nested
    class service_dialogs(Accordion):  # noqa
        ACCORDION_NAME = 'Service Dialogs'
        tree = ManageIQTree()

    configuration = Dropdown('Configuration')


class DialogForm(AutomateCustomizationView):
    title = Text('//div[@id= "main-content"]//h1')
    sub_title = Text('//div[@id= "main-content"]//h2')
    element = DialogElement()

    label = Input(id='name')
    description = Input(id="description")
    save = Button('Save')
    cancel = Button('Cancel')


class AddDialogView(DialogForm):
    create_tab = Text(locator='.//li/a[contains(@class, "create-tab")]')

    @property
    def is_displayed(self):
        expected_title = (
            "Automate Customization"
            if self.browser.product_version < "5.11"
            else "Add a new Dialog"
        )
        return (
            self.in_customization
            and self.title.text == expected_title
            and self.sub_title.text == "General"
            and self.create_tab.is_displayed
        )


class EditDialogView(DialogForm):
    save_button = Button('Save')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        obj = self.context["object"]

        expected_title = (
            "Automate Customization"
            if self.browser.product_version < "5.11"
            else 'Editing {} Service Dialog'.format(obj.label)
        )
        return (
            self.in_customization
            and self.title.text == expected_title
            and self.sub_title.text == "General"
            and self.label.read() == obj.label
        )


class CopyDialogView(DialogForm):
    save_button = Button('Save')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        obj = self.context["object"]
        expected_label = 'Copy of {}'.format(obj.label)

        expected_title = (
            "Automate Customization"
            if self.browser.product_version < "5.11"
            else 'Editing {} Service Dialog'.format(obj.label)
        )
        return (
            self.in_customization
            and self.title.text == expected_title
            and self.sub_title.text == "General"
            and self.label.read() == expected_label
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
