# -*- coding: utf-8 -*-
import attr
import re

from navmazing import NavigateToSibling, NavigateToAttribute

from widgetastic.utils import ParametrizedString, VersionPick
from widgetastic.xpath import quote
from widgetastic.widget import Checkbox, ConditionalSwitchableView, ParametrizedView, Text, View
from widgetastic_manageiq import (SummaryFormItem, FonticonPicker, PotentiallyInvisibleTab,
                                  RadioGroup, FakeWidget)
from widgetastic_patternfly import BootstrapSelect, Button, CandidateNotFound, Input

from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from cfme.utils.blockers import BZ
from cfme.utils.update import Updateable
from cfme.utils.version import Version
from cfme.utils.wait import wait_for

from . import AutomateCustomizationView


class AutomateRadioGroup(RadioGroup):
    LABELS = './/label'
    BUTTON = './/label[normalize-space(.)={}]/preceding-sibling::input[@type="radio"][1]'

    @property
    def selected(self):
        names = self.button_names
        for name in names:
            bttn = self.browser.element(self.BUTTON.format(quote(name)))
            if bttn.get_attribute('checked') is not None:
                return name
        else:
            return names[0]

    def select(self, name):
        if self.selected != name:
            self.browser.element(self.BUTTON.format(quote(name))).click()
            return True
        return False


class ButtonsAllView(AutomateCustomizationView):
    title = Text('#explorer_title_text')

    @property
    def is_displayed(self):
        return self.in_customization and self.title.text == 'All Object Types'


class ButtonFormCommon(AutomateCustomizationView):

    class options(PotentiallyInvisibleTab):  # noqa
        form = ConditionalSwitchableView(reference="type")
        type = VersionPick({
            Version.lowest(): FakeWidget(read_value='Default'),
            '5.9': BootstrapSelect('button_type')
        })

        @form.register('Default')
        class ButtonFormDefaultView(View):  # noqa
            dialog = BootstrapSelect('dialog_id')

        @form.register('Ansible Playbook')
        class ButtonFormAnsibleView(View):  # noqa
            playbook_cat_item = BootstrapSelect('service_template_id')
            inventory = AutomateRadioGroup(locator=".//input[@name='inventory']/..")
            hosts = Input(name='hosts')

        text = Input(name='name')
        display = Checkbox(name='display')
        hover = Input(name='description')
        image = VersionPick({
            Version.lowest(): BootstrapSelect('button_image'),
            '5.9': FonticonPicker('button_icon')})
        open_url = Checkbox('open_url')
        # TODO: Display for, Submit by after converted to BootstrapSelect

    class advanced(PotentiallyInvisibleTab):  # noqa
        # TODO: Enablement & Visibility
        system = BootstrapSelect('instance_name')
        message = Input(name='object_message')
        request = Input(name='object_request')

        @ParametrizedView.nested
        class attribute(ParametrizedView):  # noqa
            PARAMETERS = ('number', )
            key = Input(name=ParametrizedString('attribute_{number}'))
            value = Input(name=ParametrizedString('value_{number}'))

            @classmethod
            def all(cls, browser):
                return [(i, ) for i in range(1, 6)]

        # TODO: Role Access

    cancel_button = Button('Cancel')


class NewButtonView(ButtonFormCommon):
    title = Text('#explorer_title_text')

    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_customization and
            self.title.text == 'Adding a new Button' and
            self.buttons.is_dimmed and
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
            self.in_customization and
            # TODO: vvv BUG
            self.title.text.startswith('Adding a new Button') and
            self.buttons.is_dimmed and
            self.buttons.is_opened and
            self.buttons.tree.currently_selected == [
                'Object Types', self.context['object'].group.type,
                self.context['object'].group.text, self.context['object'].text])


class ButtonDetailView(AutomateCustomizationView):
    title = Text('#explorer_title_text')

    button_type = SummaryFormItem('Basic Information', 'Button Type')
    playbook_cat_item = SummaryFormItem('Basic Information', 'Ansible Playbook')
    target = SummaryFormItem('Basic Information', 'Target')
    text = SummaryFormItem(
        'Basic Information', VersionPick({Version.lowest(): 'Button Text', '5.9': 'Text'}),
        text_filter=lambda text: re.sub(r'\s+Display on Button\s*$', '', text))
    hover = SummaryFormItem(
        'Basic Information',
        VersionPick({Version.lowest(): 'Button Hover Text', '5.9': 'Hover Text'}))
    dialog = SummaryFormItem('Basic Information', 'Dialog')

    system = SummaryFormItem('Object Details', 'System/Process/')
    message = SummaryFormItem('Object Details', 'Message')
    request = SummaryFormItem('Object Details', 'Request')

    type = SummaryFormItem('Object Attribute', 'Type')

    show = SummaryFormItem('Visibility', 'Show')

    @property
    def is_displayed(self):
        return (
            self.in_customization and
            self.title.text == 'Button "{}"'.format(self.context['object'].text) and
            not self.buttons.is_dimmed and
            self.buttons.is_opened and
            self.buttons.tree.currently_selected == [
                'Object Types', self.context['object'].group.type,
                self.context['object'].group.text, self.context['object'].text])


class BaseButton(BaseEntity, Updateable):
    """Base class for Automate Buttons."""

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        changed = view.fill({
            'options': {
                'text': updates.get('text'),
                'hover': updates.get('hover'),
                'image': updates.get('image'),
                'open_url': updates.get('open_url'),
                'form': {
                    'dialog': updates.get('dialog'),
                    'playbook_cat_item': updates.get('playbook_cat_item'),
                    'inventory': updates.get('inventory'),
                    'hosts': updates.get('hosts')
                }
            },
            'advanced': {
                'system': updates.get('system'),
                'request': updates.get('request')
            }
        })
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(ButtonDetailView, override=updates)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            if self.appliance.version < '5.9':
                view.flash.assert_message(
                    'Button "{}" was saved'.format(updates.get('hover', self.hover)))
            else:
                view.flash.assert_message(
                    'Custom Button "{}" was saved'.format(updates.get('hover', self.hover)))
        else:
            if self.appliance.version < '5.9':
                view.flash.assert_message(
                    'Edit of Button "{}" was cancelled by the user'.format(self.text))
            else:
                view.flash.assert_message(
                    'Edit of Custom Button "{}" was cancelled by the user'.format(self.text))

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


@attr.s
class DefaultButton(BaseButton):
    group = attr.ib()
    text = attr.ib()
    hover = attr.ib()
    image = attr.ib()
    dialog = attr.ib()
    system = attr.ib(default=None)
    request = attr.ib(default=None)
    open_url = attr.ib(default=None)
    attributes = attr.ib(default=None)


@attr.s
class AnsiblePlaybookButton(BaseButton):
    group = attr.ib()
    text = attr.ib()
    hover = attr.ib()
    image = attr.ib()
    playbook_cat_item = attr.ib()
    inventory = attr.ib()
    hosts = attr.ib(default=None)
    system = attr.ib(default=None)
    request = attr.ib(default=None)
    open_url = attr.ib(default=None)
    attributes = attr.ib(default=None)


@attr.s
class ButtonCollection(BaseCollection):

    ENTITY = BaseButton

    def instantiate(self, group, text, hover, type='Default', dialog=None, playbook_cat_item=None,
                    inventory=None, hosts=None, image=None, open_url=None, system=None,
                    request=None, attributes=None):
        if image:
            pass
        elif self.appliance.version < '5.9':
            image = 'Button Image 1'
        else:
            image = 'fa-user'
        kwargs = {'open_url': open_url, 'system': system, 'request': request,
                  'attributes': attributes}
        if type == 'Default':
            button_class = DefaultButton
            args = [group, text, hover, image, dialog]
        elif type == 'Ansible Playbook':
            button_class = AnsiblePlaybookButton
            args = [group, text, hover, image, playbook_cat_item, inventory, hosts]
        return button_class.from_collection(self, *args, **kwargs)

    def create(self, text, hover, type='Default', group=None, dialog=None, playbook_cat_item=None,
               inventory=None, hosts=None, image=None, open_url=None, system=None, request=None,
               attributes=None):
        self.group = group or self.parent
        if image:
            pass
        elif self.appliance.version < '5.9':
            image = 'Button Image 1'
        else:
            image = 'fa-user'
        view = navigate_to(self, 'Add')
        view.options.fill({'type': type})
        view.fill({
            'options': {
                'text': text,
                'hover': hover,
                'image': image,
                'open_url': open_url,
                'form': {
                    'dialog': dialog,
                    'playbook_cat_item': playbook_cat_item,
                    'inventory': inventory,
                    'hosts': hosts
                }
            },
            'advanced': {'system': system, 'request': request}
        })
        if attributes is not None:
            for i, dict_ in enumerate(attributes, 1):
                view.advanced.attribute(i).fill(dict_)
        view.add_button.click()
        view = self.create_view(ButtonGroupDetailView, self.group)
        wait_for(lambda: view.is_displayed, timeout=10)
        view.flash.assert_no_error()
        if self.appliance.version < '5.9':
            view.flash.assert_message('Button "{}" was added'.format(hover))
        else:
            view.flash.assert_message('Custom Button "{}" was added'.format(hover))
        return self.instantiate(self.group, text, hover, type, dialog=dialog,
                                playbook_cat_item=playbook_cat_item, inventory=inventory,
                                hosts=hosts, image=image, open_url=open_url, system=system,
                                request=request, attributes=attributes)


@navigator.register(ButtonCollection, 'All')
class ButtonAll(CFMENavigateStep):
    VIEW = ButtonsAllView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
        self.view.buttons.tree.click_path('Object Types')


@navigator.register(ButtonCollection, 'Add')
class ButtonNew(CFMENavigateStep):
    VIEW = NewButtonView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
        self.view.buttons.tree.click_path("Object Types", self.obj.group.type, self.obj.group.text)
        self.view.configuration.item_select('Add a new Button')


@navigator.register(BaseButton, 'Details')
class ButtonDetails(CFMENavigateStep):
    VIEW = ButtonDetailView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
        self.view.buttons.tree.click_path(
            "Object Types", self.obj.group.type, self.obj.group.text, self.obj.text)


@navigator.register(BaseButton, 'Edit')
class ButtonEdit(CFMENavigateStep):
    VIEW = EditButtonView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.configuration.item_select('Edit this Button')


# Button group
class ButtonGroupObjectTypeView(AutomateCustomizationView):
    title = Text('#explorer_title_text')

    @property
    def is_displayed(self):
        return (
            self.in_customization and
            self.title.text == 'Button Groups' and
            not self.buttons.is_dimmed and
            self.buttons.is_opened and
            self.buttons.tree.currently_selected == ['Object Types', self.context['object'].type])


class ButtonGroupDetailView(AutomateCustomizationView):
    title = Text('#explorer_title_text')

    text = SummaryFormItem(
        'Basic Information',
        VersionPick({
            Version.lowest(): 'Button Group Text',
            '5.9': 'Text'}),
        text_filter=lambda text: re.sub(r'\s+Display on Button\s*$', '', text))
    hover = SummaryFormItem(
        'Basic Information',
        VersionPick({
            Version.lowest(): 'Button Group Hover Text',
            '5.9': 'Hover Text'}))

    @property
    def is_displayed(self):
        return (
            self.in_customization and
            self.title.text == 'Button Group "{}"'.format(self.context['object'].text) and
            self.buttons.is_opened and
            not self.buttons.is_dimmed and
            self.buttons.tree.currently_selected == [
                'Object Types', self.context['object'].type, self.context['object'].text])


class ButtonGroupFormCommon(AutomateCustomizationView):
    text = Input(name='name')
    display = Checkbox(name='display')
    hover = Input(name='description')
    image = VersionPick({
        Version.lowest(): BootstrapSelect('button_image'),
        '5.9': FonticonPicker('button_icon')})

    cancel_button = Button('Cancel')


class NewButtonGroupView(ButtonGroupFormCommon):
    title = Text('#explorer_title_text')

    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_customization and
            self.title.text == 'Adding a new Buttons Group' and
            self.buttons.is_dimmed and
            self.buttons.is_opened and
            self.buttons.tree.currently_selected == ['Object Types', self.context['object'].type])


class EditButtonGroupView(ButtonGroupFormCommon):
    title = Text('#explorer_title_text')

    save_button = Button(title='Save Changes')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.in_customization and
            self.title.text.startswith('Editing Buttons Group') and
            self.buttons.is_dimmed and
            self.buttons.is_opened and
            self.buttons.tree.currently_selected == [
                'Object Types', self.context['object'].type, self.context['object'].text])


@attr.s
class ButtonGroup(BaseEntity, Updateable):
    """Create,Edit and Delete Button Groups

    Args:
        text: The button Group name.
        hover: The button group hover text.
        type: The object type.
    """
    text = attr.ib()
    hover = attr.ib()
    type = attr.ib()
    image = attr.ib()

    _collections = {'buttons': ButtonCollection}

    @property
    def buttons(self):
        return self.collections.buttons

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(ButtonGroupDetailView, override=updates)
        if not BZ(1500176, forced_streams=['5.9', 'upstream']).blocks:
            assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            if self.appliance.version < '5.9':
                view.flash.assert_message(
                    'Buttons Group "{}" was saved'.format(updates.get('hover', self.hover)))
            else:
                view.flash.assert_message(
                    'Button Group "{}" was saved'.format(updates.get('hover', self.hover)))
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
            if not BZ(1500176, forced_streams=['5.9', 'upstream']).blocks:
                assert view.is_displayed
            view.flash.assert_no_error()
            if self.appliance.version < '5.9':
                view.flash.assert_message(
                    'Buttons Group "{}": Delete successful'.format(self.hover))
            else:
                view.flash.assert_message('Button Group "{}": Delete successful'.format(self.hover))

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


@attr.s
class ButtonGroupCollection(BaseCollection):
    ENTITY = ButtonGroup
    CLUSTER = "Cluster"
    DATASTORE = "Datastore"
    HOST = "Host / Node"
    PROVIDER = "Provider"
    SERVICE = "Service"
    TEMPLATE = "VM Template and Image"
    VM_INSTANCE = "VM and Instance"

    def instantiate(self, text, hover, type, image=None):
        if image:
            pass
        elif self.appliance.version < '5.9':
            image = 'Button Image 1'
        else:
            image = 'fa-user'
        return self.ENTITY.from_collection(self, text, hover, type, image)

    def create(self, text, hover, type, image=None):
        self.type = type
        if image:
            pass
        elif self.appliance.version < '5.9':
            image = 'Button Image 1'
        else:
            image = 'fa-user'
        view = navigate_to(self, 'Add')
        view.fill({
            'text': text,
            'hover': hover,
            'image': image
        })
        view.add_button.click()
        view = self.create_view(ButtonGroupObjectTypeView)

        view.flash.assert_no_error()
        if self.appliance.version < '5.9':
            view.flash.assert_message('Buttons Group "{}" was added'.format(hover))
        else:
            # checks only when bug is fixed AND version is >5.8
            if not BZ(1500176, forced_streams=['5.9', 'upstream']).blocks:
                assert view.is_displayed
            view.flash.assert_message('Button Group "{}" was added'.format(hover))
        return self.instantiate(text, hover, type, image)


@navigator.register(ButtonGroupCollection, 'All')
class ButtonGroupAll(CFMENavigateStep):
    VIEW = ButtonsAllView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
        self.view.buttons.tree.click_path('Object Types')


@navigator.register(ButtonGroupCollection, 'ObjectType')
class ButtonGroupObjectType(CFMENavigateStep):
    VIEW = ButtonGroupObjectTypeView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
        self.view.buttons.tree.click_path('Object Types', self.obj.type)


@navigator.register(ButtonGroupCollection, 'Add')
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
