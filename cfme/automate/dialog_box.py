from navmazing import NavigateToAttribute
from widgetastic_patternfly import Input, Dropdown
from cached_property import cached_property

from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


from .dialog_tab import AddTabView


class BoxForm(AddTabView):
    box_label = Input(name='group_label')
    box_desc = Input(name="group_description")


class AddBoxView(BoxForm):
    """AddBox View."""
    plus_btn = Dropdown('Add')

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == "Adding a new Dialog [Box Information]"
        )


class EditBoxView(BoxForm):
    """EditBox View."""
    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == "Editing Dialog {} [Box Information]".format(self.box_label)
        )


class BoxCollection(Navigatable):
    def __init__(self, parent, appliance=None):
        self.parent = parent
        Navigatable.__init__(self, appliance=parent.appliance)

    @property
    def tree_path(self):
        return self.parent.tree_path

    def instantiate(self, box_label=None, box_desc=None):
        return Box(self,
            box_label=box_label, box_desc=box_desc)

    def create(self, box_label=None, box_desc=None):
        """Create box method.
           Args:
             box_label and box_description.
        """
        view = navigate_to(self, "Add")
        fill_dict = {
            k: v
            for k, v in {'box_label': box_label, 'box_desc': box_desc}.items()
            if v is not None}
        view.fill(fill_dict)
        return self.instantiate(box_label=box_label, box_desc=box_desc)


class Box(Navigatable):
    """A class representing one Box of dialog."""
    def __init__(self, collection, box_label, box_desc):
        Navigatable.__init__(self, appliance=collection.appliance)
        self.collection = collection
        self.box_label = box_label
        self.box_desc = box_desc

    @property
    def parent(self):
        """returns the parent object - Tab"""
        return self.collection.parent

    @cached_property
    def elements(self):
        from .dialog_element import ElementCollection
        return ElementCollection(self)

    @property
    def tree_path(self):
        return self.collection.tree_path + [self.box_label]

    @property
    def tab(self):
        return self.parent.dialog


@navigator.register(BoxCollection)
class Add(CFMENavigateStep):
    VIEW = AddBoxView

    prerequisite = NavigateToAttribute('parent.collection', 'Add')

    def step(self):
        self.prerequisite_view.plus_btn.item_select("Add a new Box to this Tab")
