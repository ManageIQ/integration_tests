# -*- coding: utf-8 -*-
import re

import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import ParametrizedString
from widgetastic.widget import Checkbox
from widgetastic.widget import ColourInput
from widgetastic.widget import ConditionalSwitchableView
from widgetastic.widget import ParametrizedView
from widgetastic.widget import Select
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from . import AutomateCustomizationView
from cfme.base.ui import AutomateSimulationView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.update import Updateable
from widgetastic_manageiq import AutomateRadioGroup
from widgetastic_manageiq import FonticonPicker
from widgetastic_manageiq import MultiBoxOrderedSelect
from widgetastic_manageiq import PotentiallyInvisibleTab
from widgetastic_manageiq import RolesSelector
from widgetastic_manageiq import SummaryFormItem
from widgetastic_manageiq.expression_editor import ExpressionEditor


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
    "Virtual Infra Switch",
]


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

        role_show = BootstrapSelect(id="visibility_typ")
        roles = RolesSelector(locator="//label[contains(text(),'User Roles')]/../div/table")

    cancel_button = Button("Cancel")


class NewButtonView(ButtonFormCommon):
    title = Text("#explorer_title_text")
    paste = Button(title="Paste object details for use in a Button.")

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
    user_roles = SummaryFormItem("Visibility", "User Roles")

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
                "advanced": {
                    "system": updates.get("system"),
                    "request": updates.get("request"),
                    "role_show": updates.get("role_show"),
                    "roles": updates.get("roles"),
                },
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

    def simulate(
        self,
        target_object,
        instance="Request",
        message="create",
        request="InspectMe",
        execute_methods=True,
        attributes_values=None,
        reset=False,
        cancel=False,
    ):
        view = navigate_to(self, "simulate")

        # Group and User are EVM type objects. workaround for <5.11
        target_type = (
            "EVM {}".format(self.group.type)
            if self.group.type in ["Group", "User"] and self.appliance.version < "5.11"
            else self.group.type
        )

        changed = view.fill(
            {
                "instance": instance,
                "message": message,
                "request": request,
                "target_type": target_type,
                "target_object": target_object,
                "execute_methods": execute_methods,
                "avp": attributes_values,
            }
        )

        if cancel:
            view.cancel_button.click()
            return None

        if changed:
            if reset:
                view.reset_button.click()
            else:
                view.submit_button.click()
            view.flash.assert_no_error()

    @property
    def user_roles(self):
        """This property use to check roles

        Return: `To All` if button not assigned to specific role else `list` of roles
        """
        view = navigate_to(self, "Details")
        show = view.show.read()
        return show if show == "To All" else view.user_roles.read().split(", ")


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
        roles: button assigned to specific roles
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
    roles = attr.ib(default=None)


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
        roles: button assigned to specific roles
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
    roles = attr.ib(default=None)


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
        roles=None,
    ):
        kwargs = {
            "display": display,
            "open_url": open_url,
            "system": system,
            "request": request,
            "attributes": attributes,
            "visibility": visibility,
            "enablement": enablement,
            "roles": roles,
        }
        if type == "Default":
            button_class = DefaultButton
            args = [group, text, hover, image, dialog]
        elif type == "Ansible Playbook":
            button_class = AnsiblePlaybookButton
            args = [group, text, hover, image, playbook_cat_item, inventory]
            kwargs["hosts"] = hosts
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
        roles=None,
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
            # TODO: extend visibility expression variations if needed.
            if self.group.type in EVM_TAG_OBJS:
                tag = "EVM {obj_type}.{tag}".format(
                    obj_type=self.group.type, tag=visibility["tag"]
                )
            elif self.group.type in BUILD_TAG_OBJS:
                _type = "Switch" if self.group.type == "Virtual Infra Switch" else self.group.type
                tag = "{obj_type}.Build.{tag}".format(obj_type=_type, tag=visibility["tag"])
            else:
                tag = "{obj_type}.{tag}".format(obj_type=self.group.type, tag=visibility["tag"])

            if view.advanced.visibility.define_exp.is_displayed:
                view.advanced.visibility.define_exp.click()
            view.advanced.visibility.expression.fill_tag(tag=tag, value=visibility["value"])

        if enablement:
            # TODO: extend enablement expression variations if needed.
            if self.group.type in EVM_TAG_OBJS:
                tag = "EVM {obj_type}.{tag}".format(
                    obj_type=self.group.type, tag=enablement["tag"]
                )
            elif self.group.type in BUILD_TAG_OBJS:
                _type = "Switch" if self.group.type == "Virtual Infra Switch" else self.group.type
                tag = "{obj_type}.Build.{tag}".format(obj_type=_type, tag=enablement["tag"])
            else:
                tag = "{obj_type}.{tag}".format(obj_type=self.group.type, tag=enablement["tag"])

            if view.advanced.enablement.define_exp.is_displayed:
                view.advanced.enablement.define_exp.click()

            view.advanced.enablement.expression.fill_tag(tag=tag, value=enablement["value"])
            view.advanced.enablement.disabled_text.fill(
                "Tag - {} : {}".format(enablement["tag"], enablement["value"])
            )

        view.fill({"advanced": {"system": system, "request": request}})

        if attributes is not None:
            for i, attribute in enumerate(attributes, 1):
                view.advanced.attribute(i).fill({"key": attribute[0], "value": attribute[1]})

        if roles:
            view.advanced.role_show.fill("<By Role>")
            view.advanced.roles.wait_displayed("20s")
            view.advanced.roles.fill(roles)
        else:
            view.advanced.role_show.fill("<To All>")

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
            roles=roles,
        )


@navigator.register(ButtonCollection, "All")
class ButtonAll(CFMENavigateStep):
    VIEW = ButtonsAllView
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")

    def step(self, *args, **kwargs):
        self.view.buttons.tree.click_path("Object Types")


@navigator.register(ButtonCollection, "Add")
class ButtonNew(CFMENavigateStep):
    VIEW = NewButtonView
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")

    def step(self, *args, **kwargs):
        self.view.buttons.tree.click_path("Object Types", self.obj.group.type, self.obj.group.text)
        self.view.configuration.item_select("Add a new Button")


@navigator.register(BaseButton, "Details")
class ButtonDetails(CFMENavigateStep):
    VIEW = ButtonDetailView
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")

    def step(self, *args, **kwargs):
        self.view.buttons.tree.click_path(
            "Object Types", self.obj.group.type, self.obj.group.text, self.obj.text
        )


@navigator.register(BaseButton, "Edit")
class ButtonEdit(CFMENavigateStep):
    VIEW = EditButtonView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.view.configuration.item_select("Edit this Button")


@navigator.register(BaseButton, "simulate")
class ButtonSimulation(CFMENavigateStep):
    VIEW = AutomateSimulationView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Simulate")


# Button group
class ButtonGroupObjectTypeView(AutomateCustomizationView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        expected_title = (
            "Button Groups"
            if self.browser.product_version < "5.11"
            else "{} Button Groups".format(self.context["object"].type)
        )
        return (
            self.in_customization
            and self.title.text == expected_title
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
        obj = self.context["object"]

        if obj.text == "[Unassigned Buttons]":
            expected_title = '{} Button Group "{}"'.format(obj.type, "Unassigned Buttons")
        else:
            expected_title = (
                'Button Group "{}"'.format(obj.text)
                if self.browser.product_version < "5.11"
                else '{} Button Group "{}"'.format(obj.type, obj.text)
            )

        return (
            self.in_customization
            and self.title.text == expected_title
            and self.buttons.is_opened
            and not self.buttons.is_dimmed
            and self.buttons.tree.currently_selected == ["Object Types", obj.type, obj.text]
        )


class ButtonGroupFormCommon(AutomateCustomizationView):
    text = Input(name="name")
    display = Checkbox(name="display")
    hover = Input(name="description")
    image = FonticonPicker("button_icon")
    icon_color = ColourInput(id="button_color")
    assign_buttons = MultiBoxOrderedSelect(
        available_items="available_fields",
        chosen_items="selected_fields",
        move_into="Move selected fields right",
        move_from="Move selected fields left",
        move_up="Move selected fields up",
        move_down="Move selected fields down",
    )
    cancel_button = Button("Cancel")


class NewButtonGroupView(ButtonGroupFormCommon):
    title = Text("#explorer_title_text")

    add_button = Button("Add")

    @property
    def is_displayed(self):
        expected_title = "Adding a new {} Group".format("Button")
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
        expected_title = "Editing {} Group".format("Button")

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
        assign_buttons: List of assigned buttons to Group.
    """

    text = attr.ib()
    hover = attr.ib()
    type = attr.ib()
    image = attr.ib(default="fa-user")
    display = attr.ib(default=None)
    icon_color = attr.ib(default=None)
    assign_buttons = attr.ib(default=None)

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

    def create(
        self,
        text,
        hover,
        type,
        image="fa-user",
        display=None,
        icon_color=None,
        assign_buttons=None,
    ):
        self.type = type

        view = navigate_to(self, "Add")
        view.fill(
            {
                "text": text,
                "hover": hover,
                "image": image,
                "display": display,
                "icon_color": icon_color,
                "assign_buttons": assign_buttons,
            }
        )
        view.add_button.click()
        view = self.create_view(ButtonGroupObjectTypeView)

        view.flash.assert_no_error()
        view.flash.assert_message('Button Group "{}" was added'.format(hover))
        return self.instantiate(
            text=text,
            hover=hover,
            type=type,
            image=image,
            display=display,
            icon_color=icon_color,
            assign_buttons=assign_buttons,
        )


@navigator.register(ButtonGroupCollection, "All")
class ButtonGroupAll(CFMENavigateStep):
    VIEW = ButtonsAllView
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")

    def step(self, *args, **kwargs):
        self.view.buttons.tree.click_path("Object Types")


@navigator.register(ButtonGroupCollection, "ObjectType")
class ButtonGroupObjectType(CFMENavigateStep):
    VIEW = ButtonGroupObjectTypeView
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")

    def step(self, *args, **kwargs):
        self.view.buttons.tree.click_path("Object Types", self.obj.type)


@navigator.register(ButtonGroupCollection, "Add")
class ButtonGroupNew(CFMENavigateStep):
    VIEW = NewButtonGroupView
    prerequisite = NavigateToSibling("ObjectType")

    def step(self, *args, **kwargs):
        self.view.configuration.item_select("Add a new Button Group")


@navigator.register(ButtonGroup, "Details")
class ButtonGroupDetails(CFMENavigateStep):
    VIEW = ButtonGroupDetailView
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")

    def step(self, *args, **kwargs):
        self.view.buttons.tree.click_path("Object Types", self.obj.type, self.obj.text)


@navigator.register(ButtonGroup, "Edit")
class ButtonGroupEdit(CFMENavigateStep):
    VIEW = EditButtonGroupView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.view.configuration.item_select("Edit this Button Group")
