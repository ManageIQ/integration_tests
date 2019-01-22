# -*- coding: utf-8 -*-
import attr
import re

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.utils import ParametrizedString
from widgetastic.widget import (
    Checkbox,
    ColourInput,
    ConditionalSwitchableView,
    ParametrizedView,
    Select,
    Text,
    View,
)
from widgetastic.xpath import quote
from widgetastic_patternfly import BootstrapSelect, Button, CandidateNotFound, Input

from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigate_to, navigator
from cfme.utils.update import Updateable
from widgetastic_manageiq import (
    FonticonPicker,
    PotentiallyInvisibleTab,
    RadioGroup,
    SummaryFormItem,
)
from widgetastic_manageiq.expression_editor import ExpressionEditor

from . import AutomateCustomizationView


EVM_TAG_OBJS = ["Group", "User"]

BUILD_TAG_OBJS = [
    "Availability Zone",
    "Cloud Network",
    "Cloud Object Store Container",
    "Cloud Subnet",
    "Network Router",
    "Security Group",
    "Tenant",
    "Container Volume",
    "Generic Object",
    "Virtual Infra Switch",
    "Cloud Tenant",
    "Cloud Volume",
    "Load Balancer",
    "Orchestration Stack",
]


class AutomateRadioGroup(RadioGroup):
    LABELS = ".//label"
    BUTTON = './/label[normalize-space(.)={}]/preceding-sibling::input[@type="radio"][1]'

    @property
    def selected(self):
        names = self.button_names
        for name in names:
            bttn = self.browser.element(self.BUTTON.format(quote(name)))
            if bttn.get_attribute("checked") is not None:
                return name
        else:
            return names[0]

    def select(self, name):
        if self.selected != name:
            self.browser.element(self.BUTTON.format(quote(name))).click()
            return True
        return False


class ButtonsAllView(AutomateCustomizationView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return self.in_customization and self.title.text == "All Object Types"


class ButtonFormCommon(AutomateCustomizationView):
    class options(PotentiallyInvisibleTab):  # noqa
        form = ConditionalSwitchableView(reference="type")
        type = BootstrapSelect("button_type")

        @form.register("Default")
        class ButtonFormDefaultView(View):  # noqa
            dialog = BootstrapSelect("dialog_id")

        @form.register("Ansible Playbook")
        class ButtonFormAnsibleView(View):  # noqa
            playbook_cat_item = BootstrapSelect("service_template_id")
            inventory = AutomateRadioGroup(locator=".//input[@name='inventory']/..")
            hosts = Input(name="hosts")

        text = Input(name="name")
        display = Checkbox(name="display")
        hover = Input(name="description")
        image = FonticonPicker("button_icon")
        icon_color = ColourInput(id="button_color")
        open_url = Checkbox("open_url")
        display_for = Select(id="display_for")
        submit = Select(id="submit_how")

    class advanced(PotentiallyInvisibleTab):  # noqa
        @View.nested
        class enablement(View):  # noqa
            title = Text('//*[@id="ab_form"]/div[1]/h3')
            define_exp = Text(locator='//*[@id="form_enablement_expression_div"]//a/button')
            expression = ExpressionEditor()
            disabled_text = Input(id="disabled_text")

        @View.nested
        class visibility(View):  # noqa
            title = Text('//*[@id="ab_form"]/h3[2]')
            define_exp = Text(locator='//*[@id="form_visibility_expression_div"]//a/button')
            expression = ExpressionEditor()

        system = BootstrapSelect("instance_name")
        message = Input(name="object_message")
        request = Input(name="object_request")

        @ParametrizedView.nested
        class attribute(ParametrizedView):  # noqa
            PARAMETERS = ("number",)
            key = Input(name=ParametrizedString("attribute_{number}"))
            value = Input(name=ParametrizedString("value_{number}"))

            @classmethod
            def all(cls, browser):
                return [(i,) for i in range(1, 6)]

        # TODO: Role Access

    cancel_button = Button("Cancel")


class NewButtonView(ButtonFormCommon):
    title = Text("#explorer_title_text")

    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_customization
            and self.title.text == "Adding a new Button"
            and self.buttons.is_dimmed
            and self.buttons.is_opened
            and self.buttons.tree.currently_selected
            == [
                "Object Types",
                self.context["object"].group.type,
                self.context["object"].group.text,
            ]
        )


class EditButtonView(ButtonFormCommon):
    title = Text("#explorer_title_text")

    save_button = Button(title="Save Changes")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_customization
            and self.title.text.startswith("Editing Button")
            and self.buttons.is_dimmed
            and self.buttons.is_opened
            and self.buttons.tree.currently_selected
            == [
                "Object Types",
                self.context["object"].group.type,
                self.context["object"].group.text,
                self.context["object"].text,
            ]
        )


class ButtonDetailView(AutomateCustomizationView):
    title = Text("#explorer_title_text")

    button_type = SummaryFormItem("Basic Information", "Button Type")
    playbook_cat_item = SummaryFormItem("Basic Information", "Ansible Playbook")
    target = SummaryFormItem("Basic Information", "Target")
    text = SummaryFormItem(
        "Basic Information",
        "Text",
        text_filter=lambda text: re.sub(r"\s+Display on Button\s*$", "", text),
    )
    hover = SummaryFormItem("Basic Information", "Hover Text")
    dialog = SummaryFormItem("Basic Information", "Dialog")

    system = SummaryFormItem("Object Details", "System/Process/")
    message = SummaryFormItem("Object Details", "Message")
    request = SummaryFormItem("Object Details", "Request")

    type = SummaryFormItem("Object Attribute", "Type")

    show = SummaryFormItem("Visibility", "Show")

    @property
    def is_displayed(self):
        return (
            self.in_customization
            and self.title.text == 'Button "{}"'.format(self.context["object"].text)
            and not self.buttons.is_dimmed
            and self.buttons.is_opened
            and self.buttons.tree.currently_selected
            == [
                "Object Types",
                self.context["object"].group.type,
                self.context["object"].group.text,
                self.context["object"].text,
            ]
        )


class BaseButton(BaseEntity, Updateable):
    """Base class for Automate Buttons."""

    def update(self, updates):
        view = navigate_to(self, "Edit")
        changed = view.fill(
            {
                "options": {
                    "text": updates.get("text"),
                    "hover": updates.get("hover"),
                    "image": updates.get("image"),
                    "open_url": updates.get("open_url"),
                    "form": {
                        "dialog": updates.get("dialog"),
                        "playbook_cat_item": updates.get("playbook_cat_item"),
                        "inventory": updates.get("inventory"),
                        "hosts": updates.get("hosts"),
                    },
                },
                "advanced": {"system": updates.get("system"), "request": updates.get("request")},
            }
        )
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(ButtonDetailView, override=updates, wait="10s")
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Custom Button "{}" was saved'.format(updates.get("hover", self.hover))
            )
        else:
            view.flash.assert_message(
                'Edit of Custom Button "{}" was cancelled by the user'.format(self.text)
            )

    def delete(self, cancel=False):
        view = navigate_to(self, "Details")
        view.configuration.item_select("Remove this Button", handle_alert=not cancel)

        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view = self.create_view(ButtonGroupDetailView, self.group, wait="10s")
            view.flash.assert_no_error()
            view.flash.assert_message('Button "{}": Delete successful'.format(self.hover))

    @property
    def exists(self):
        try:
            navigate_to(self, "Details")
            return True
        except CandidateNotFound:
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()


@attr.s
class DefaultButton(BaseButton):
    """Default type Button Entity Class

    Args:
        group: Button Group object
        text: The button name.
        hover: The button hover text.
        image: Icon of button.
        dialog: Dialog object attached to button.
        display: Button name display on Button.
        system: Button pointing to System/Process
        request: Button pointing to request method
        open_url: Open url with button
        attributes: Button attribute
        visibility: Visibility expression in terms of tag and its value
        enablement: Enablement expression in terms of tag and its value
    """
    group = attr.ib()
    text = attr.ib()
    hover = attr.ib()
    image = attr.ib()
    dialog = attr.ib()
    display = attr.ib(default=None)
    system = attr.ib(default=None)
    request = attr.ib(default=None)
    open_url = attr.ib(default=None)
    attributes = attr.ib(default=None)
    visibility = attr.ib(default=None)
    enablement = attr.ib(default=None)


@attr.s
class AnsiblePlaybookButton(BaseButton):
    """Ansible Playbook type Button Entity Class

    Args:
        group: Button Group object
        text: The button name.
        hover: The button hover text.
        image: Icon of button.
        playbook_cat_item: Playbook catalog item.
        display: Button name display on Button.
        inventory: Pointing to host
        hosts: Specific host
        system: Button pointing to System/Process
        request: Button pointing to request method
        open_url: Open url with button
        attributes: Button attribute
        visibility: Visibility expression in terms of tag and its value
        enablement: Enablement expression in terms of tag and its value
    """
    group = attr.ib()
    text = attr.ib()
    hover = attr.ib()
    image = attr.ib()
    playbook_cat_item = attr.ib()
    inventory = attr.ib()
    display = attr.ib(default=None)
    hosts = attr.ib(default=None)
    system = attr.ib(default=None)
    request = attr.ib(default=None)
    open_url = attr.ib(default=None)
    attributes = attr.ib(default=None)
    visibility = attr.ib(default=None)
    enablement = attr.ib(default=None)


@attr.s
class ButtonCollection(BaseCollection):

    ENTITY = BaseButton

    def instantiate(
        self,
        group,
        text,
        hover,
        image="fa-user",
        type="Default",
        display=None,
        dialog=None,
        display_for=None,
        submit=None,
        playbook_cat_item=None,
        inventory=None,
        hosts=None,
        open_url=None,
        system=None,
        request=None,
        attributes=None,
        visibility=None,
        enablement=None,
    ):
        kwargs = {
            "display": display,
            "open_url": open_url,
            "system": system,
            "request": request,
            "attributes": attributes,
            "visibility": visibility,
            "enablement": enablement,
        }
        if type == "Default":
            button_class = DefaultButton
            args = [group, text, hover, image, dialog]
        elif type == "Ansible Playbook":
            button_class = AnsiblePlaybookButton
            args = [group, text, hover, image, playbook_cat_item, inventory, hosts]
        return button_class.from_collection(self, *args, **kwargs)

    def create(
        self,
        text,
        hover,
        type="Default",
        image="fa-user",
        display=None,
        group=None,
        dialog=None,
        display_for=None,
        submit=None,
        playbook_cat_item=None,
        inventory=None,
        hosts=None,
        open_url=None,
        system=None,
        request=None,
        attributes=None,
        visibility=None,
        enablement=None,
    ):
        self.group = group or self.parent

        view = navigate_to(self, "Add")
        view.options.fill({"type": type})
        view.fill(
            {
                "options": {
                    "text": text,
                    "display": display,
                    "hover": hover,
                    "image": image,
                    "open_url": open_url,
                    "display_for": display_for,
                    "submit": submit,
                    "form": {
                        "dialog": dialog,
                        "playbook_cat_item": playbook_cat_item,
                        "inventory": inventory,
                        "hosts": hosts,
                    },
                }
            }
        )

        if visibility:
            # ToDo: extend visibility expression variations if needed.
            if self.group.type in EVM_TAG_OBJS:
                tag = "EVM {obj_type}.{tag}".format(
                    obj_type=self.group.type, tag=visibility["tag"]
                )
            elif self.group.type in BUILD_TAG_OBJS:
                tag = "{obj_type}.Build.{tag}".format(
                    obj_type=self.group.type, tag=visibility["tag"]
                )
            else:
                tag = "{obj_type}.{tag}".format(obj_type=self.group.type, tag=visibility["tag"])

            if view.advanced.visibility.define_exp.is_displayed:
                view.advanced.visibility.define_exp.click()
            view.advanced.visibility.expression.fill_tag(tag=tag, value=visibility["value"])

        if enablement:
            # ToDo: extend enablement expression variations if needed.
            if self.group.type in EVM_TAG_OBJS:
                tag = "EVM {obj_type}.{tag}".format(
                    obj_type=self.group.type, tag=enablement["tag"]
                )
            elif self.group.type in BUILD_TAG_OBJS:
                tag = "{obj_type}.Build.{tag}".format(
                    obj_type=self.group.type, tag=enablement["tag"]
                )
            else:
                tag = "{obj_type}.{tag}".format(obj_type=self.group.type, tag=enablement["tag"])

            if view.advanced.enablement.define_exp.is_displayed:
                view.advanced.enablement.define_exp.click()

            view.advanced.enablement.expression.fill_tag(tag=tag, value=enablement["value"])

        view.fill({"advanced": {"system": system, "request": request}})

        if attributes is not None:
            for i, dict_ in enumerate(attributes, 1):
                view.advanced.attribute(i).fill(dict_)

        view.add_button.click()
        view = self.create_view(ButtonGroupDetailView, self.group, wait="15s")
        view.flash.assert_no_error()
        view.flash.assert_message('Custom Button "{}" was added'.format(hover))

        return self.instantiate(
            self.group,
            text=text,
            hover=hover,
            type=type,
            display=display,
            dialog=dialog,
            display_for=display_for,
            submit=submit,
            playbook_cat_item=playbook_cat_item,
            inventory=inventory,
            hosts=hosts,
            image=image,
            open_url=open_url,
            system=system,
            request=request,
            attributes=attributes,
            visibility=visibility,
            enablement=enablement,
        )


@navigator.register(ButtonCollection, "All")
class ButtonAll(CFMENavigateStep):
    VIEW = ButtonsAllView
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")

    def step(self):
        self.view.buttons.tree.click_path("Object Types")


@navigator.register(ButtonCollection, "Add")
class ButtonNew(CFMENavigateStep):
    VIEW = NewButtonView
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")

    def step(self):
        self.view.buttons.tree.click_path("Object Types", self.obj.group.type, self.obj.group.text)
        self.view.configuration.item_select("Add a new Button")


@navigator.register(BaseButton, "Details")
class ButtonDetails(CFMENavigateStep):
    VIEW = ButtonDetailView
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")

    def step(self):
        self.view.buttons.tree.click_path(
            "Object Types", self.obj.group.type, self.obj.group.text, self.obj.text
        )


@navigator.register(BaseButton, "Edit")
class ButtonEdit(CFMENavigateStep):
    VIEW = EditButtonView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.view.configuration.item_select("Edit this Button")


# Button group
class ButtonGroupObjectTypeView(AutomateCustomizationView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_customization
            and self.title.text == "Button Groups"
            and not self.buttons.is_dimmed
            and self.buttons.is_opened
            and self.buttons.tree.currently_selected
            == ["Object Types", self.context["object"].type]
        )


class ButtonGroupDetailView(AutomateCustomizationView):
    title = Text("#explorer_title_text")

    text = SummaryFormItem(
        "Basic Information",
        "Text",
        text_filter=lambda text: re.sub(r"\s+Display on Button\s*$", "", text),
    )
    hover = SummaryFormItem("Basic Information", "Hover Text")

    @property
    def is_displayed(self):
        # Unassigned Buttons is default group for each custom button object
        expected_title = (
            '{} Button Group "Unassigned Buttons"'.format(self.context["object"].type)
            if self.context["object"].text == "[Unassigned Buttons]"
            else 'Button Group "{}"'.format(self.context["object"].text)
        )

        return (
            self.in_customization
            and self.title.text == expected_title
            and self.buttons.is_opened
            and not self.buttons.is_dimmed
            and self.buttons.tree.currently_selected
            == ["Object Types", self.context["object"].type, self.context["object"].text]
        )


class ButtonGroupFormCommon(AutomateCustomizationView):
    text = Input(name="name")
    display = Checkbox(name="display")
    hover = Input(name="description")
    image = FonticonPicker("button_icon")
    icon_color = ColourInput(id="button_color")

    cancel_button = Button("Cancel")


class NewButtonGroupView(ButtonGroupFormCommon):
    title = Text("#explorer_title_text")

    add_button = Button("Add")

    @property
    def is_displayed(self):
        ver = self.browser.appliance.version
        expected_title = "Adding a new {} Group".format("Buttons" if ver < "5.10" else "Button")
        return (
            self.in_customization
            and self.title.text == expected_title
            and self.buttons.is_dimmed
            and self.buttons.is_opened
            and self.buttons.tree.currently_selected
            == ["Object Types", self.context["object"].type]
        )


class EditButtonGroupView(ButtonGroupFormCommon):
    title = Text("#explorer_title_text")

    save_button = Button(title="Save Changes")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        ver = self.browser.appliance.version
        expected_title = "Editing {} Group".format("Buttons" if ver < "5.10" else "Button")

        return (
            self.in_customization
            and self.title.text.startswith(expected_title)
            and self.buttons.is_dimmed
            and self.buttons.is_opened
            and self.buttons.tree.currently_selected
            == ["Object Types", self.context["object"].type, self.context["object"].text]
        )


@attr.s
class ButtonGroup(BaseEntity, Updateable):
    """Create,Edit and Delete Button Groups

    Args:
        text: The button Group name.
        hover: The button group hover text.
        type: The object type.
        image: Icon of Group.
        display: Group name display on Button.
        icon_color: Icon Color of Group.
    """

    text = attr.ib()
    hover = attr.ib()
    type = attr.ib()
    image = attr.ib()
    display = attr.ib(default=None)
    icon_color = attr.ib(default=None)

    _collections = {"buttons": ButtonCollection}

    @property
    def buttons(self):
        return self.collections.buttons

    def update(self, updates):
        view = navigate_to(self, "Edit")
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(ButtonGroupDetailView, override=updates, wait="10s")
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Button Group "{}" was saved'.format(updates.get("hover", self.hover))
            )
        else:
            view.flash.assert_message(
                'Edit of Buttons Group "{}" was cancelled by the user'.format(self.text)
            )

    def delete(self, cancel=False):
        view = navigate_to(self, "Details")
        view.configuration.item_select("Remove this Button Group", handle_alert=not cancel)

        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view = self.create_view(ButtonGroupObjectTypeView, wait="10s")
            view.flash.assert_no_error()
            view.flash.assert_message('Button Group "{}": Delete successful'.format(self.hover))

    @property
    def exists(self):
        try:
            navigate_to(self, "Details")
            return True
        except CandidateNotFound:
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()


@attr.s
class ButtonGroupCollection(BaseCollection):
    ENTITY = ButtonGroup
    AZONE = "Availability Zone"
    CLOUD_NETWORK = "Cloud Network"
    CLOUD_OBJECT_STORE_CONTAINER = "Cloud Object Store Container"
    CLOUD_SUBNET = "Cloud Subnet"
    CLOUD_TENANT = "Cloud Tenant"
    CLOUD_VOLUME = "Cloud Volume"
    CLUSTERS = "Cluster / Deployment Role"
    CONTAINER_IMAGES = "Container Image"
    CONTAINER_NODES = "Container Node"
    CONTAINER_PODS = "Container Pod"
    CONTAINER_PROJECTS = "Container Project"
    CONTAINER_TEMPLATES = "Container Template"
    CONTAINER_VOLUMES = "Container Volume"
    DATASTORES = "Datastore"
    GROUP = "Group"
    USER = "User"
    GENERIC = "Generic Object"
    HOSTS = "Host / Node"
    LOAD_BALANCER = "Load Balancer"
    ROUTER = "Network Router"
    ORCHESTRATION_STACK = "Orchestration Stack"
    PROVIDER = "Provider"
    SECURITY_GROUP = "Security Group"
    SERVICE = "Service"
    SWITCH = "Virtual Infra Switch"
    TENANT = "Tenant"
    TEMPLATE_IMAGE = "VM Template and Image"
    VM_INSTANCE = "VM and Instance"

    def instantiate(self, text, hover, type, image=None, display=None, icon_color=None):
        self.type = type
        if not image:
            image = "fa-user"
        return self.ENTITY.from_collection(self, text, hover, type, image, display, icon_color)

    def create(self, text, hover, type, image=None, display=None, icon_color=None):
        self.type = type

        # Icon selection is Mandatory
        if not image:
            image = "fa-user"

        view = navigate_to(self, "Add")
        view.fill(
            {
                "text": text,
                "hover": hover,
                "image": image,
                "display": display,
                "icon_color": icon_color,
            }
        )
        view.add_button.click()
        view = self.create_view(ButtonGroupObjectTypeView)

        view.flash.assert_no_error()
        view.flash.assert_message('Button Group "{}" was added'.format(hover))
        return self.instantiate(
            text=text, hover=hover, type=type, image=image, display=display, icon_color=icon_color
        )


@navigator.register(ButtonGroupCollection, "All")
class ButtonGroupAll(CFMENavigateStep):
    VIEW = ButtonsAllView
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")

    def step(self):
        self.view.buttons.tree.click_path("Object Types")


@navigator.register(ButtonGroupCollection, "ObjectType")
class ButtonGroupObjectType(CFMENavigateStep):
    VIEW = ButtonGroupObjectTypeView
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")

    def step(self):
        self.view.buttons.tree.click_path("Object Types", self.obj.type)


@navigator.register(ButtonGroupCollection, "Add")
class ButtonGroupNew(CFMENavigateStep):
    VIEW = NewButtonGroupView
    prerequisite = NavigateToSibling("ObjectType")

    def step(self):
        self.view.configuration.item_select("Add a new Button Group")


@navigator.register(ButtonGroup, "Details")
class ButtonGroupDetails(CFMENavigateStep):
    VIEW = ButtonGroupDetailView
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")

    def step(self):
        self.view.buttons.tree.click_path("Object Types", self.obj.type, self.obj.text)


@navigator.register(ButtonGroup, "Edit")
class ButtonGroupEdit(CFMENavigateStep):
    VIEW = EditButtonGroupView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.view.configuration.item_select("Edit this Button Group")
