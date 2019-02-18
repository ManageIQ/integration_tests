# -*- coding: utf-8 -*-
"""Page model for Cloud Intel / Reports / Dashboard Widgets / Menus"""
import attr

from . import BaseDashboardReportWidget
from . import BaseDashboardWidgetFormCommon
from . import BaseEditDashboardWidgetStep
from . import BaseEditDashboardWidgetView
from . import BaseNewDashboardWidgetStep
from . import BaseNewDashboardWidgetView
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import MenuShortcutsPicker


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


@attr.s
class MenuWidget(BaseDashboardReportWidget):

    TYPE = "Menus"
    TITLE = "Menu"
    pretty_attrs = ["description", "shortcuts", "visibility"]
    shortcuts = attr.ib(default=None)

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
