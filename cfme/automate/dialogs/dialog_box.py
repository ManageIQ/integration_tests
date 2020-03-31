import attr
from cached_property import cached_property
from navmazing import NavigateToAttribute

from cfme.automate.dialogs import AddBoxView
from cfme.automate.dialogs import BoxForm
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.modeling.base import parent_of_type
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator


class EditBoxView(BoxForm):
    """EditBox View."""
    @property
    def is_displayed(self):
        return (
            self.in_customization and
            self.title.text == f"Editing Dialog {self.box_label} [Box Information]"
        )


@attr.s
class Box(BaseEntity):
    """A class representing one Box of dialog."""
    box_label = attr.ib()
    box_desc = attr.ib(default=None)

    from cfme.automate.dialogs.dialog_element import ElementCollection
    _collections = {'elements': ElementCollection}

    @cached_property
    def elements(self):
        return self.collections.elements

    @property
    def tree_path(self):
        return self.parent.tree_path + [self.box_label]

    @property
    def tab(self):
        from cfme.automate.dialogs.dialog_tab import Tab
        return parent_of_type(self, Tab)


@attr.s
class BoxCollection(BaseCollection):

    ENTITY = Box

    @property
    def tree_path(self):
        return self.parent.tree_path

    def create(self, box_label=None, box_desc=None):
        """Create box method.
           Args:
             box_label and box_description.
        """
        view = navigate_to(self, "Add")
        view.new_box.click()
        view.edit_box.click()
        view.fill({'box_label': box_label, 'box_desc': box_desc})
        view.save_button.click()
        return self.instantiate(box_label=box_label, box_desc=box_desc)


@navigator.register(BoxCollection)
class Add(CFMENavigateStep):
    VIEW = AddBoxView

    prerequisite = NavigateToAttribute('parent.parent', 'Add')

    def step(self, *args, **kwargs):
        self.prerequisite_view.add_section.click()
