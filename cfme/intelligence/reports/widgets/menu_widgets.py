# -*- coding: utf-8 -*-
"""Page model for Cloud Intel / Reports / Dashboard Widgets / Menus"""
from widgetastic_manageiq import MenuShortcutsPicker

from utils.appliance.implementations.ui import navigator
from . import (
    DashboardWidgetFormCommon,
    EditDashboardWidget,
    EditDashboardWidgetView,
    NewDashboardWidget,
    NewDashboardWidgetView,
    ReportsDashboardWidget
)


class MenuWidgetFormCommon(DashboardWidgetFormCommon):

    menu_shortcuts = MenuShortcutsPicker(
        "form_filter_div",
        select_id="add_shortcut",
        names_locator=".//input[starts-with(@name, 'shortcut_desc_')]",
        remove_locator=".//input[@value={}]/../a[@title='Remove this Shortcut']"
    )


class NewMenuWidgetView(NewDashboardWidgetView, MenuWidgetFormCommon):
    pass


class EditMenuWidgetView(EditDashboardWidgetView, MenuWidgetFormCommon):
    pass


class MenuWidget(ReportsDashboardWidget):

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
