from widgetastic.widget import Text, Checkbox
from widgetastic_manageiq import MenuShortcutsPicker
from utils.appliance.implementations.ui import navigator
from widgetastic_patternfly import Button, Input, BootstrapSelect
from . import (Widget, DashboardWidgetsView, NewDashboardWidget, EditDashboardWidget,
    NewDashboardWidgetView, EditDashboardWidgetView)


class MenuWidgetsFormCommon(DashboardWidgetsView):

    title = Text("#explorer_title_text")
    widget_title = Input(name="title")
    description = Input(name="description")
    active = Checkbox("enabled")
    menu_shortcuts = MenuShortcutsPicker(
        "form_filter_div",
        select_id="add_shortcut",
        names_locator=".//input[starts-with(@name, 'shortcut_desc_')]",
        remove_locator=".//input[@value={}]/../a[@title='Remove this Shortcut']"
    )
    visibility = BootstrapSelect("visibility_typ")
    cancel_button = Button("Cancel")


class NewMenuWidgetView(NewDashboardWidgetView, MenuWidgetsFormCommon):
    pass


class EditMenuWidgetView(EditDashboardWidgetView, MenuWidgetsFormCommon):
    pass


class MenuWidget(Widget):

    TYPE = "Menus"
    TITLE = "Menu"
    pretty_attrs = ["description", "shortcuts", "visibility"]

    def __init__(self, title, description=None, active=None, shortcuts=None, visibility=None):
        self.title = title
        self.description = description
        self.active = active
        self.shortcuts = shortcuts
        self.visibility = visibility

    @property
    def fill_dict(self):
        return {
            "widget_title": self.title,
            "description": self.description,
            "active": self.active,
            "menu_shortcuts": self.shortcuts,
            "visibility": self.visibility
        }


@navigator.register(MenuWidget, "Add")
class NewMenuWidget(NewDashboardWidget):
    VIEW = NewMenuWidgetView


@navigator.register(MenuWidget, "Edit")
class EditMenuWidget(EditDashboardWidget):
    VIEW = EditMenuWidgetView
