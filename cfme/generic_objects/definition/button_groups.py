import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling

from cfme.exceptions import OptionNotAvailable
from cfme.generic_objects.definition.definition_views import GenericObjectActionsDetailsView
from cfme.generic_objects.definition.definition_views import GenericObjectAddButtonView
from cfme.generic_objects.definition.definition_views import GenericObjectButtonDetailsView
from cfme.generic_objects.definition.definition_views import GenericObjectButtonGroupAddView
from cfme.generic_objects.definition.definition_views import GenericObjectButtonGroupDetailsView
from cfme.generic_objects.definition.definition_views import GenericObjectButtonGroupEditView
from cfme.generic_objects.definition.definition_views import GenericObjectDefinitionAllView
from cfme.generic_objects.definition.definition_views import GenericObjectDefinitionDetailsView
from cfme.generic_objects.definition.definition_views import GenericObjectEditButtonView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.update import Updateable
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker


@attr.s
class GenericObjectButton(BaseEntity, Updateable):
    REMOVE_TEXT = VersionPicker({
        "5.11": 'Remove this Custom Button from Inventory',
        Version.lowest(): 'Remove this Button from Inventory'}
    )

    name = attr.ib()
    description = attr.ib()
    request = attr.ib()
    image = attr.ib(default='fa-home')
    button_type = attr.ib(default='Default')
    display = attr.ib(default=True)
    dialog = attr.ib(default=None)
    open_url = attr.ib(default=None)
    display_for = attr.ib(default=None)
    submit_version = attr.ib(default=None)
    system_message = attr.ib(default=None)
    attributes = attr.ib(default=None)
    role = attr.ib(default=None)
    button_group = attr.ib(default=None)

    # extra fields for ansible playbook type buttons
    playbook_cat_item = attr.ib(default=None)
    inventory = attr.ib(default=None)
    hosts = attr.ib(default=None)

    def delete(self, cancel=False):
        """Delete generic object button

            Args: cancel(bool): By default button will be deleted, pass True to cancel deletion
        """
        view = navigate_to(self, 'Details')
        view.configuration.item_select(self.REMOVE_TEXT, handle_alert=not cancel)
        view = self.create_view(GenericObjectDefinitionAllView)
        assert view.is_displayed
        view.flash.assert_no_error()

    def update(self, updates):
        """Update this button in UI.

        Args:
            updates: Provided by update() context manager.
        """
        view = navigate_to(self, "Edit")
        view.fill_with(updates, on_change=view.save, no_change=view.cancel)

        view.flash.assert_no_error()


@attr.s
class GenericObjectButtonsCollection(BaseCollection):

    ENTITY = GenericObjectButton

    def create(self, name, description, request, image='fa-home', button_type='Default',
               display=True, dialog=None, open_url=None, display_for=None, submit_version=None,
               system_message=None, attributes=None, role=None, cancel=False, inventory=None,
               playbook_cat_item=None, hosts=None):
        """Add button to generic object definition or button group

            Args:
                name(str): button name
                description(str): button description
                request(str): button request type
                image(str): button image
                button_type(str): button type
                display(bool): parameter to display button on UI or not, default is True
                dialog(str): button dialog
                open_url(str): button open_url
                display_for(str): for which item this button should be displayed
                submit_version(str): how this button should be submited, ex. 'One by one'
                system_message(str): button submit message
                attributes(dict): button attributes ex. {'address': 'string'}
                role: role used for button
                cancel(bool): cancel button creation, default if False
                inventory(str): Name of inventory (Localhost, Target Machine, Specific Hosts)
                playbook_cat_item(str): catalog item name for ansible playbook
                hosts(str): if inventory is Specific Hosts, enter hosts here

            Returns: button object

        """
        view = navigate_to(self, 'Add')

        view.fill({
            'button_type': button_type,
            'form': {
                'playbook_cat_item': playbook_cat_item, 'inventory': inventory, 'hosts': hosts
            },
            'name': name,
            'description': description,
            'display': display,
            'image': image,
            'open_url': open_url,
            'display_for': display_for,
            'request': request,
            'submit_version': submit_version,
            'system_message': system_message
        })
        # TODO: for some reason this was not being filled if included in dict above
        if dialog:
            view.fill({"dialog": dialog})
        if attributes:
            for name, type in attributes.items():
                view.attribute_value_table.fill([{'Name': name}, {'Value': type}])
        if isinstance(role, dict):
            view.role.select('<By Role>')
            # todo select roles
        if cancel:
            view.cancel.click()
        else:
            view.add.click()
        view.flash.assert_no_error()
        return self.instantiate(name=name, description=description, request=request, image=image,
                                button_type=button_type, display=display, dialog=dialog,
                                open_url=open_url, display_for=display_for,
                                submit_version=submit_version, system_message=system_message,
                                attributes=attributes, role=role, inventory=inventory,
                                playbook_cat_item=playbook_cat_item, hosts=hosts)

    def all(self):
        """All existing buttons

        Returns: list of buttons objects
        """
        buttons = []
        view = navigate_to(self, 'All')
        for row in view.button_table:
            image_class = view.browser.get_attribute(
                'class', view.browser.element('./i', parent=row[0].__locator__()))
            buttons.append(self.instantiate(name=row.text.text, description=row.hover_text.text,
                                            image=image_class.split(' ')[1]))
        return buttons


@navigator.register(GenericObjectButtonsCollection, 'Add')
class ButtonAdd(CFMENavigateStep):
    VIEW = GenericObjectAddButtonView

    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Add a new Button')


@navigator.register(GenericObjectButtonsCollection, 'All')
class ButtonAll(CFMENavigateStep):
    @property
    def VIEW(self):  # noqa
        if isinstance(self.obj.parent, GenericObjectButtonGroup):
            return GenericObjectButtonGroupDetailsView
        else:
            return GenericObjectActionsDetailsView

    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self, *args, **kwargs):
        if not isinstance(self.obj.parent, GenericObjectButtonGroup):
            self.prerequisite_view.accordion.classes.tree.click_path(
                'All Generic Object Classes', self.obj.parent.name, 'Actions')


@navigator.register(GenericObjectButton, 'Details')
class ButtonDetails(CFMENavigateStep):
    VIEW = GenericObjectButtonDetailsView

    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        path = self.prerequisite_view.accordion.classes.tree.read()
        path.append(self.obj.name)
        self.prerequisite_view.accordion.classes.tree.fill(path)


@navigator.register(GenericObjectButton, "Edit")
class ButtonEdit(CFMENavigateStep):
    VIEW = GenericObjectEditButtonView

    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Edit this Button")


@attr.s
class GenericObjectButtonGroup(BaseEntity, Updateable):
    REMOVE_TEXT = VersionPicker({
        "5.11": 'Remove this Custom Button Group from Inventory',
        Version.lowest(): 'Remove this Button Group from Inventory'}
    )

    name = attr.ib()
    description = attr.ib()
    image = attr.ib()
    display = attr.ib(default=True)

    _collections = {'generic_object_buttons': GenericObjectButtonsCollection}

    def delete(self, cancel=False):
        """Delete generic object button group

            Args: cancel(bool): By default group will be deleted, pass True to cancel deletion
        """
        view = navigate_to(self, 'Details')

        if not view.configuration.item_enabled(self.REMOVE_TEXT):
            raise OptionNotAvailable(
                "Remove this Button Group is not enabled, there are buttons assigned to this group")
        else:
            view.configuration.item_select(
                self.REMOVE_TEXT, handle_alert=not cancel
            )
        view = self.create_view(GenericObjectDefinitionAllView, wait=10)
        view.flash.assert_no_error()

    def update(self, updates):
        """Update this button in UI.

        Args:
            updates: Provided by update() context manager.
        """
        view = navigate_to(self, "Edit")
        view.fill_with(updates, on_change=view.save, no_change=view.cancel)

        view.flash.assert_no_error()


@attr.s
class GenericObjectButtonGroupsCollection(BaseCollection):

    ENTITY = GenericObjectButtonGroup

    def create(self, name, description, image, display=True, cancel=False):
        """Add button group for generic object definition

            Args:
                name(str): button group name
                description(str): button group description
                image(str): button group image
                display(bool): parameter to display button group on UI or not, default is True
                cancel(bool): cancel button creation, default if False

            Returns: button group object

        """
        view = navigate_to(self, 'Add')
        view.fill({
            'image': image,
            'name': name,
            'description': description,
            'display': display,
        })
        if cancel:
            view.cancel.click()
        else:
            view.add.click()
        view = self.parent.create_view(GenericObjectDefinitionDetailsView, wait=10)
        view.flash.assert_no_error()
        group = self.instantiate(name=name, description=description, image=image, display=display)
        return group

    def all(self):
        """All existing button groups

            Returns: list of button groups objects
        """
        groups = []
        view = navigate_to(self, 'All')
        all_groups = view.group_table
        for row in all_groups:
            image_class = view.browser.get_attribute(
                'class', view.browser.element('./i', parent=row[0].__locator__()))
            groups.append(self.instantiate(name=row.text.text, description=row.hover_text.text,
                                           image=image_class.split(' ')[1]))
        return groups


@navigator.register(GenericObjectButtonGroupsCollection, 'All')
class ButtonGroupAll(CFMENavigateStep):
    VIEW = GenericObjectActionsDetailsView

    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.accordion.classes.tree.click_path(
            'All Generic Object Classes', self.obj.parent.name, 'Actions')


@navigator.register(GenericObjectButtonGroupsCollection, 'Add')
class ButtonGroupAdd(CFMENavigateStep):
    VIEW = GenericObjectButtonGroupAddView

    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Add a new Button Group')


@navigator.register(GenericObjectButtonGroup, 'Details')
class ButtonGroupDetails(CFMENavigateStep):
    VIEW = GenericObjectButtonGroupDetailsView

    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.accordion.classes.tree.click_path(
            'All Generic Object Classes', self.obj.parent.parent.name, 'Actions',
            f'{self.obj.name} (Group)')


@navigator.register(GenericObjectButtonGroup, "Edit")
class ButtonGroupEdit(CFMENavigateStep):
    VIEW = GenericObjectButtonGroupEditView

    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Edit this Button Group")
