from navmazing import NavigateToAttribute
from widgetastic.widget import Text
from widgetastic_patternfly import Input, Dropdown
from cached_property import cached_property

from cfme.utils.appliance import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from .service_dialogs import AddDialogView


class TabForm(AddDialogView):
    tab_label = Input(name='tab_label')
    tab_desc = Input(name="tab_description")


class AddTabView(TabForm):

    plus_btn = Dropdown('Add')

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == "Adding a new Dialog [Tab Information]"
        )


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


class TabCollection(BaseCollection):
    def __init__(self, appliance, parent):
        self.parent = parent
        self.appliance = appliance

    @property
    def tree_path(self):
        return self.parent.tree_path

    def instantiate(self, tab_label=None, tab_desc=None):
        return Tab(self,
            tab_label=tab_label, tab_desc=tab_desc)

    def add_tab(self):
        view = navigate_to(self, "AddTab")
        view.plus_btn.item_select("Add a new Tab to this Dialog")

    def create(self, tab_label=None, tab_desc=None):
        """ Create tab method"""
        view = navigate_to(self, "Add")
        fill_dict = {
            k: v
            for k, v in {'tab_label': tab_label, 'tab_desc': tab_desc}.items()
            if v is not None}
        view.fill(fill_dict)
        return self.instantiate(tab_label=tab_label, tab_desc=tab_desc)


class Tab(BaseEntity):
    """A class representing one Tab in the UI."""
    def __init__(self, collection, tab_label, tab_desc):
        self.collection = collection
        self.appliance = self.collection.appliance
        self.tab_label = tab_label
        self.tab_desc = tab_desc

    @property
    def parent(self):
        """ Returns parent object - Dialog"""
        return self.collection.parent

    @cached_property
    def boxes(self):
        from .dialog_box import BoxCollection
        return BoxCollection(self.appliance, self)

    @property
    def tree_path(self):
        return self.collection.tree_path + [self.tab_label]

    @property
    def dialog(self):
        """ Returns parent object - Dialog"""
        return self.parent


@navigator.register(TabCollection)
class Add(CFMENavigateStep):
    VIEW = AddTabView

    prerequisite = NavigateToAttribute('parent.collection', 'Add')

    def step(self):
        self.prerequisite_view.plus_btn.item_select("Add a new Tab to this Dialog")
