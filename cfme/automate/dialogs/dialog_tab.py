import attr

from navmazing import NavigateToAttribute
from widgetastic.widget import Text

from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to

from . import TabForm, AddTabView
from .dialog_box import BoxCollection


class EditTabView(TabForm):

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == "Editing Dialog {} [Tab Information]".format(self.tab_label)
        )


class DetailsTabView(TabForm):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == 'Dialog "{}"'.format(self.context['object'].tab_label)
        )


@attr.s
class Tab(BaseEntity):
    """A class representing one Tab in the UI."""
    tab_label = attr.ib()
    tab_desc = attr.ib(default=None)

    _collections = {'boxes': BoxCollection}

    @property
    def boxes(self):
        return self.collections.boxes

    @property
    def tree_path(self):
        return self.parent.tree_path + [self.tab_label]

    @property
    def dialog(self):
        """ Returns parent object - Dialog"""
        from .service_dialogs import Dialog
        return parent_of_type(self, Dialog)


@attr.s
class TabCollection(BaseCollection):

    ENTITY = Tab

    @property
    def tree_path(self):
        return self.parent.tree_path

    def create(self, tab_label=None, tab_desc=None):
        """ Create tab method"""
        view = navigate_to(self, "Add")
        view.new_tab.click()
        view.edit_tab.click()
        view.fill({'tab_label': tab_label, 'tab_desc': tab_desc})
        view.save_button.click()
        return self.instantiate(tab_label=tab_label, tab_desc=tab_desc)


@navigator.register(TabCollection)
class Add(CFMENavigateStep):
    VIEW = AddTabView

    prerequisite = NavigateToAttribute('parent.parent', 'Add')

    def step(self):
        self.prerequisite_view.create_tab.click()
