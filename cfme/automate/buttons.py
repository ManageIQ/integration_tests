# -*- coding: utf-8 -*-
import re

from navmazing import NavigateToSibling, NavigateToAttribute

from widgetastic.widget import Text, Checkbox
from widgetastic.utils import VersionPick
from widgetastic_manageiq import SummaryFormItem
from widgetastic_patternfly import BootstrapSelect, Button, Input

from widgetastic_patternfly import CandidateNotFound
from utils.appliance import Navigatable
from utils.appliance.endpoints.ui import navigator, navigate_to, CFMENavigateStep
from utils.update import Updateable
from utils import version

from . import AutomateCustomizationView


class ButtonsAllView(AutomateCustomizationView):
    title = Text('#explorer_title_text')

    @property
    def is_displayed(self):
        return super(ButtonsAllView, self).is_displayed and self.title.text == 'All Object Types'


class ButtonGroupObjectTypeView(AutomateCustomizationView):
    title = Text('#explorer_title_text')

    @property
    def is_displayed(self):
        return (
            super(ButtonGroupObjectTypeView, self).is_displayed and
            self.title.text == 'Button Groups' and
            self.buttons.is_opened and
            self.buttons.tree.currently_selected == ['Object Types', self.context['object'].type])


class ButtonGroupDetailView(AutomateCustomizationView):
    title = Text('#explorer_title_text')

    text = SummaryFormItem(
        'Basic Information', 'Button Text',
        text_filter=lambda text: re.sub(r'\s+Display on Button\s*$', '', text))
    hover = SummaryFormItem('Basic Information', 'Button Hover Text')

    @property
    def is_displayed(self):
        return (
            super(ButtonGroupDetailView, self).is_displayed and
            self.title.text == 'Button Group "{}"'.format(self.context['object'].text) and
            self.buttons.is_opened and
            self.buttons.tree.currently_selected == [
                'Object Types', self.context['object'].type, self.context['object'].text])


class ButtonGroupFormCommon(AutomateCustomizationView):
    text = Input(name='name')
    display = Checkbox(name='display')
    hover = Input(name='description')
    image = BootstrapSelect('button_image')

    cancel_button = Button('Cancel')


class NewButtonGroupView(ButtonGroupFormCommon):
    title = Text('#explorer_title_text')

    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            super(NewButtonGroupView, self).is_displayed and
            self.title.text == 'Adding a new Buttons Group' and
            self.buttons.is_opened and
            self.buttons.tree.currently_selected == ['Object Types', self.context['object'].type])


class EditButtonGroupView(ButtonGroupFormCommon):
    title = Text('#explorer_title_text')

    save_button = Button(title='Save Changes')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            super(EditButtonGroupView, self).is_displayed and
            self.title.text.startswith('Editing Buttons Group') and
            self.buttons.is_opened and
            self.buttons.tree.currently_selected == [
                'Object Types', self.context['object'].type, self.context['object'].text])


class ButtonGroup(Updateable, Navigatable):
    """Create,Edit and Delete Button Groups

    Args:
        text: The button Group name.
        hover: The button group hover text.
        type: The object type.
    """
    CLUSTER = "Cluster"
    DATASTORE = "Datastore"
    HOST = VersionPick({
        version.LOWEST: "Host",
        '5.4': "Host / Node"}
    )
    PROVIDER = "Provider"
    SERVICE = "Service"
    TEMPLATE = "VM Template and Image"
    VM_INSTANCE = "VM and Instance"

    def __init__(self, text=None, hover=None, type=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.text = text
        self.hover = hover
        self.type = type

    def create(self):
        view = navigate_to(self, 'Add')
        view.fill({
            'text': self.text,
            'hover': self.hover,
            'image': 'Button Image 1',
        })
        view.add_button.click()
        view = self.create_view(ButtonGroupObjectTypeView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_message('Buttons Group "{}" was added'.format(self.hover))

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(ButtonGroupDetailView)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Buttons Group "{}" was saved'.format(updates.get('hover', self.hover)))
        else:
            view.flash.assert_message(
                'Edit of Buttons Group "{}" was cancelled by the user'.format(self.text))

    def delete(self, cancel=False):
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Remove this Button Group', handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view = self.create_view(ButtonGroupObjectTypeView)
            assert view.is_displayed
            view.flash.assert_no_error()
            view.flash.assert_message('Buttons Group "{}": Delete successful'.format(self.hover))

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()


@navigator.register(ButtonGroup, 'All')
class ButtonGroupAll(CFMENavigateStep):
    VIEW = ButtonsAllView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
        self.view.buttons.tree.click_path('Object Types')


@navigator.register(ButtonGroup, 'ObjectType')
class ButtonGroupObjectType(CFMENavigateStep):
    VIEW = ButtonGroupObjectTypeView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
        self.view.buttons.tree.click_path('Object Types', self.obj.type)


@navigator.register(ButtonGroup, 'Add')
class ButtonGroupNew(CFMENavigateStep):
    VIEW = NewButtonGroupView
    prerequisite = NavigateToSibling('ObjectType')

    def step(self):
        self.view.configuration.item_select('Add a new Button Group')


@navigator.register(ButtonGroup, 'Details')
class ButtonGroupDetails(CFMENavigateStep):
    VIEW = ButtonGroupDetailView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
        self.view.buttons.tree.click_path(
            'Object Types', self.obj.type, self.obj.text)


@navigator.register(ButtonGroup, 'Edit')
class ButtonGroupEdit(CFMENavigateStep):
    VIEW = EditButtonGroupView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.configuration.item_select('Edit this Button Group')


# Button
class ButtonFormCommon(AutomateCustomizationView):
    text = Input(name='name')
    display = Checkbox(name='display')
    hover = Input(name='description')
    image = BootstrapSelect('button_image')
    dialog = BootstrapSelect('dialog_id')
    system = BootstrapSelect('instance_name')
    message = Input(name='object_message')
    request = Input(name='object_request')
    # TODO: AVP and Visibility

    cancel = Button('Cancel')


class NewButtonView(ButtonFormCommon):
    title = Text('#explorer_title_text')

    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            super(NewButtonView, self).is_displayed and
            self.title.text == 'Adding a new Button' and
            self.buttons.is_opened and
            self.buttons.tree.currently_selected == [
                'Object Types', self.context['object'].group.type,
                self.context['object'].group.text])


class EditButtonView(ButtonFormCommon):
    title = Text('#explorer_title_text')

    save_button = Button(title='Save Changes')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            super(EditButtonView, self).is_displayed and
            # TODO: vvv BUG
            self.title.text.startswith('Adding a new Button') and
            self.buttons.is_opened and
            self.buttons.tree.currently_selected == [
                'Object Types', self.context['object'].group.type,
                self.context['object'].group.text, self.context['object'].text])


class ButtonDetailView(AutomateCustomizationView):
    title = Text('#explorer_title_text')

    text = SummaryFormItem(
        'Basic Information', 'Button Text',
        text_filter=lambda text: re.sub(r'\s+Display on Button\s*$', '', text))
    hover = SummaryFormItem('Basic Information', 'Button Hover Text')
    dialog = SummaryFormItem('Basic Information', 'Dialog')

    system = SummaryFormItem('Object Details', 'System/Process/')
    message = SummaryFormItem('Object Details', 'Message')
    request = SummaryFormItem('Object Details', 'Request')

    type = SummaryFormItem('Object Attribute', 'Type')

    show = SummaryFormItem('Visibility', 'Show')

    @property
    def is_displayed(self):
        return (
            super(ButtonDetailView, self).is_displayed and
            self.title.text == 'Button "{}"'.format(self.context['object'].text) and
            self.buttons.is_opened and
            self.buttons.tree.currently_selected == [
                'Object Types', self.context['object'].group.type,
                self.context['object'].group.text, self.context['object'].text])


class Button(Updateable, Navigatable):
    """Create,Edit and Delete buttons under a Button

    Args:
        group: Group where this button belongs.
        text: The button name.
        hover: The button hover text.
        dialog: The dialog to be selected for a button.
        system: System or Processes , DropDown to choose Automation/Request.
    """

    def __init__(self, group=None, text=None,
                 hover=None, dialog=None,
                 system=None, request=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.group = group
        self.text = text
        self.hover = hover
        self.dialog = dialog
        self.system = system
        self.request = request

    def create(self):
        view = navigate_to(self, 'Add')
        view.fill({
            'text': self.text,
            'hover': self.hover,
            'dialog': self.dialog,
            'system': self.system,
            'request': self.request,
            'image': 'Button Image 1'
        })
        view.add_button.click()
        view = self.create_view(ButtonGroupDetailView, self.group)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_message('Button "{}" was added'.format(self.hover))

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(ButtonDetailView)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Button "{}" was saved'.format(updates.get('hover', self.hover)))
        else:
            view.flash.assert_message(
                'Edit of Button "{}" was cancelled by the user'.format(self.text))

    def delete(self, cancel=False):
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Remove this Button', handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view = self.create_view(ButtonGroupDetailView, self.group)
            assert view.is_displayed
            view.flash.assert_no_error()
            view.flash.assert_message('Button "{}": Delete successful'.format(self.hover))

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()


@navigator.register(Button, 'All')
class ButtonAll(CFMENavigateStep):
    VIEW = ButtonsAllView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
        self.view.buttons.tree.click_path('Object Types')


@navigator.register(Button, 'Add')
class ButtonNew(CFMENavigateStep):
    VIEW = NewButtonView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
        self.view.buttons.tree.click_path("Object Types", self.obj.group.type, self.obj.group.text)
        self.view.configuration.item_select('Add a new Button')


@navigator.register(Button, 'Details')
class ButtonDetails(CFMENavigateStep):
    VIEW = ButtonDetailView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
        self.view.buttons.tree.click_path(
            "Object Types", self.obj.group.type, self.obj.group.text, self.obj.text)


@navigator.register(Button, 'Edit')
class ButtonEdit(CFMENavigateStep):
    VIEW = EditButtonView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.configuration.item_select('Edit this Button')
