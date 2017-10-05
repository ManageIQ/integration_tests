# -*- coding: utf-8 -*-
"""Page model for Cloud Intel / Reports / Dashboard Widgets / Menus"""
from widgetastic_manageiq import MenuShortcutsPicker

from cfme.utils.appliance.implementations.ui import navigator
from . import (
    BaseDashboardReportWidget,
    BaseDashboardWidgetFormCommon,
    BaseEditDashboardWidgetStep,
    BaseEditDashboardWidgetView,
    BaseNewDashboardWidgetStep,
    BaseNewDashboardWidgetView
)


class MenuWidgetFormCommon(BaseDashboardWidgetFormCommon):

    menu_shortcuts = MenuShortcutsPicker(
        "form_filter_div",
        select_id="add_shortcut",
        names_locator=".//input[starts-with(@name, 'shortcut_desc_')]"
    )


class NewMenuWidgetView(BaseNewDashboardWidgetView, MenuWidgetFormCommon):
    pass


class EditMenuWidgetView(BaseEditDashboardWidgetView, MenuWidgetFormCommon):
    pass


class MenuWidget(BaseDashboardReportWidget):

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
class NewMenuWidget(BaseNewDashboardWidgetStep):
    VIEW = NewMenuWidgetView


@navigator.register(MenuWidget, "Edit")
class EditMenuWidget(BaseEditDashboardWidgetStep):
    VIEW = EditMenuWidgetView
